# GPS tiles viewer

Small Leaflet page to look at the tiles served by the gps-tile dev server.

- `index.html`: the viewer. Reads `areas.json` for the "Area" dropdown.
- `update-areas.py`: builds `areas.json` from the shape data on the server.

Update the area list:

    ./update-areas.py root@<host> 20

Then commit `areas.json` and push. GitHub Pages serves the `main` branch.
