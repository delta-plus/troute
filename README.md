# Troute  
Terminal Route-Finder  
  
Usage: troute (-c [city, state]) (-p) (-r) (-x) [start] [destination]  
  
Troute finds the shortest path between two street addresses while optionally avoiding certain locations.  
The resulting route is displayed as text, which allows Troute to be used entirely from the terminal.  
  
After the initial downloads for a city of the user's choice, Troute runs fully offline on OSM data.  
The start and destination can usually be provided as coordinates, names, or addresses.  
This depends on the location. Coordinates are the most reliable and always work offline.  
If using a place name, the city must be provided with the "-c" flag.  
  
Downloads:  
In order to use Troute, you will need to download a GraphML file for the city of your choice.  
Troute will prompt for this upon the first run, creating the directory structure below.  
<pre>
.  
└── [state]  
    └── [city]  
        ├── constraints.txt (optional, see below)  
        ├── map.graphml  
        └── map.osm (optional, see below)  
</pre>
  
Offline Use:  
For offline use of Troute, you will additionally need an OSM XML file for the same city.  
This will be used to convert addresses and names to coordinates without using a web API.  
It is recommended to use BBBike to obtain this file (https://extract.bbbike.org).  
If you'd instead like to use a web API for conversions, use the "-r" (for "remote") option.  
  
Constraints:  
Constraints may be provided as a file of names, addresses, or coordinate pairs, one per line.  
This file will be ignored by default. Turn on constraint-based routing with "-x".  
  
Output:  
By default, Troute will display the resulting route map until a key is pressed.  
Users may also use "-p" to print the resulting route map to standard output.  
  
  
## Examples  
Unconstrained routing with street addresses.  
`troute -p '709 N Monroe St, Spokane, WA' '125 S Stevens St, Spokane, WA'`  
![doc](examples/troute.png)
  
Routing with constraints set to avoid the Ridler Piano Bar.  
In this example, names are used instead of addresses.  
`troute -c 'spokane, wa' -px "indy's barbershop" 'berserk'`  
![doc](examples/troute2.png)
  
  
## Notes  
• The OSM and constraints files required to run the example commands above can be found in the examples directory.  
• As there is currently no support for changing the scale of the map or scrolling, routes past a certain size will fail.  
• Inter-city routing is currently not supported either. Sorry.  
• The location types do not have to match. For example, the start can be an address with the destination as a name.  
• If using the "-c" flag, the city and state can be omitted from addresses.  
• Results may vary. Use at your own risk/curiosity.  
