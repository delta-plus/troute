#!/usr/bin/python3

import os
import sys
import math
import argparse

import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points

FORBIDDEN_RADIUS_METERS = 20 # ~96 ft


# ============================================================
# STEP 1 — Build Graph
# ============================================================

def build_or_load_graph(graph_path):
  if os.path.exists(graph_path):
    G = ox.load_graphml(graph_path)
    return G

  print('Enter city in the format [city], [state/region], [country].\n', end='', file=sys.stderr, flush=True)
  print('Example: Spokane, Washington, USA\n', end='', file=sys.stderr, flush=True)
  print('>> ', end='', file=sys.stderr, flush=True)
  boundary = ox.geocode_to_gdf(input())

  # Build drivable road graph
  G = ox.graph_from_polygon(
    boundary.geometry.iloc[0],
    network_type="drive"
  )

  # Project to metric CRS for distance accuracy
  G = ox.project_graph(G)

  # Restrict routing to city limits
  boundary = boundary.to_crs(G.graph["crs"])
  city_poly = boundary.geometry.iloc[0]

  nodes, edges = ox.graph_to_gdfs(G)
  edges = edges[edges.within(city_poly)]

  G = ox.graph_from_gdfs(nodes, edges)
  ox.save_graphml(G, graph_path)

  return G


# ============================================================
# STEP 2 — Remove Forbidden Segments
# ============================================================

def remove_forbidden_edges(G, forbidden_file):
  if not forbidden_file:
    return G

  edges = ox.graph_to_gdfs(G, nodes=False)

  # Load forbidden coordinates
  forbidden_points = []
  with open(forbidden_file, "r") as f:
    for line in f:
      lat, lon = map(float, line.strip().split(","))
      forbidden_points.append(Point(lon, lat))

  # Convert to GeoSeries and project
  forbidden_gdf = gpd.GeoSeries(forbidden_points, crs="EPSG:4326")
  forbidden_gdf = forbidden_gdf.to_crs(G.graph["crs"])

  for point in forbidden_gdf:
    buffer = point.buffer(FORBIDDEN_RADIUS_METERS)

    # Use spatial index automatically via geopandas
    matches = edges[edges.intersects(buffer)]

    for idx in matches.index:
      u, v, key = idx
      if G.has_edge(u, v, key):
        G.remove_edge(u, v, key)

  return G


# ============================================================
# STEP 3 — Snap Coordinates to Graph
# ============================================================

def snap_to_graph(G, lat, lon):
  point = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
  point = point.to_crs(G.graph["crs"])
  x = point.geometry.iloc[0].x
  y = point.geometry.iloc[0].y

  return ox.nearest_nodes(G, X=x, Y=y)


# ============================================================
# STEP 4 — Generate Turn-by-Turn Directions
# ============================================================

def calculate_bearing(p1, p2):
  dx = p2.x - p1.x
  dy = p2.y - p1.y
  angle = math.degrees(math.atan2(dx, dy))

  return (angle + 360) % 360


def classify_turn(angle_diff):
  if abs(angle_diff) < 15:
    return "Straight"
  elif 15 <= angle_diff < 135:
    return "Right"
  elif -135 < angle_diff <= -15:
    return "Left"
  else:
    return "Sharp turn"


def generate_directions(G, route):
  edges = ox.graph_to_gdfs(G, nodes=False)
  directions = []
  next = ''

  prev_bearing = None
  prev_street = None
  accumulated_length = 0

  for u, v in zip(route[:-1], route[1:]):
    edge_data = G.get_edge_data(u, v)
    edge = list(edge_data.values())[0]

    street = edge.get("name", "Unnamed Road")
    length = edge.get("length", 0)

    geom = edge.get("geometry")
    if geom is None:
      continue

    start = geom.coords[0]
    end = geom.coords[-1]

    p1 = Point(start)
    p2 = Point(end)

    bearing = calculate_bearing(p1, p2)

    if prev_bearing is None:
      directions.append(f"{street}: ")
      prev_bearing = bearing
      prev_street = street
      accumulated_length = length
      continue

    angle_diff = bearing - prev_bearing
    if angle_diff > 180:
      angle_diff -= 360
    elif angle_diff < -180:
      angle_diff += 360

    turn = classify_turn(angle_diff)

    if street == prev_street:
      accumulated_length += length
    else:
      miles = accumulated_length * 0.000621371
      directions.append(f"{miles:.2f} miles\n")
      directions.append(f"{turn} on {street}: ")
      accumulated_length = length
      miles = accumulated_length * 0.000621371
      next = f"{miles:.2f} miles"
      prev_street = street

    prev_bearing = bearing

  directions.append(next)

  return directions


# ============================================================
# STEP 5 — Main Router
# ============================================================

def route(start_lat, start_lon, dest_lat, dest_lon, graph_path, forbidden_file=None):
  G = build_or_load_graph(graph_path)
  G = remove_forbidden_edges(G, forbidden_file)

  orig_node = snap_to_graph(G, start_lat, start_lon)
  dest_node = snap_to_graph(G, dest_lat, dest_lon)

  try:
    route = nx.shortest_path(G, orig_node, dest_node, weight="length")
  except nx.NetworkXNoPath:
    print("No route found (constraints may disconnect graph).")
    return

  directions = generate_directions(G, route)

  result = ''
  for d in directions:
    result += d

  print(result)


# ============================================================
# CLI ENTRY
# ============================================================

if __name__ == "__main__":
  try:
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--start", required=True)
    parser.add_argument("-d", "--dest", required=True)
    parser.add_argument("-m", "--map", required=True)
    parser.add_argument("-x", "--constraints", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    start_lat, start_lon = map(float, args.start.split(","))
    dest_lat, dest_lon = map(float, args.dest.split(","))
    constraints_path = "maps/" + args.map + "/constraints.txt"
    graph_path = "maps/" + args.map + "/map.graphml"

    if args.constraints and os.path.isfile(constraints_path):
      route(start_lat, start_lon, dest_lat, dest_lon, graph_path, constraints_path)
    else:
      route(start_lat, start_lon, dest_lat, dest_lon, graph_path)
  except Exception as e:
    print('Routing failed. Check arguments.')
    exit(1)
