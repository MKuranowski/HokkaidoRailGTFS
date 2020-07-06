# HokkaidoRailGTFS

## Description
Creates GTFS file with JR Hokkaido and South Hokkaido Railway data.
Hokkaido Shinkansen schedules are omitted.


## Requirements
[Python3](https://www.python.org) (version 3.6 or later) is required with 5 additional libraries:
- [requests](https://pypi.org/project/requests/),
- [Beautiful Soup 4](https://pypi.org/project/beautifulsoup4/),
- [parsec](https://pypi.org/project/parsec/)
- [pyyaml](https://pypi.org/project/PyYAML/)
- [pytz](https://pypi.org/project/pytz/).

All python requirements can be installed with `pip3 install -U -r requirements.txt`.


## Running
`python3 hokkaidorail.py`. After a while the GTFS file, hokkaidorail.zip, will be ready.


## GTFS Compliance
In general, the produced feed follows the [GTFS-JP](https://www.gtfs.jp/developpers-guide/format-reference.html) standard, with 2 exceptions:
1. Routes aren't splitted by direction,
2. Fare information is omitted.


## IDs & Colors

Direction ID: 0 means "down" (下り), 1 means "up" (上り).  
Route colors are based on <https://www.jrhokkaido.co.jp/global/pdf/e-route_map.pdf>.


| Line Name                          | JR Code | GTFS ID | Color   | Color Example                                                  |
|-----------------------------------------|----|---------|---------|----------------------------------------------------------------|
| Hakodate Main Line (Hakodate~Oshamambe) | H  | 100     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Muroran Main Line (Oshamambe~H-Muroran) | H  | 101     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Muroran Main Line (H-Muroran~Tomakomai) | H  | 102     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Chitose Line                            | H  | 103     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Hakodate Main Line (Otaru~Sapporo)      | S  | 104     | #FF0000 | ![red](https://via.placeholder.com/12/FF0000/?text=+)          |
| Hakodate Main Line (Sapporo~Asahikawa)  | A  | 105     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Hakodate Main Line (Oshamambe~Otaru)    | S  | 106     | #FF0000 | ![red](https://via.placeholder.com/12/FF0000/?text=+)          |
| Sekihoku Main Line                      | A  | 107     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Sekishō Line                            | K  | 108     | #9ACD32 | ![yellowgreen](https://via.placeholder.com/12/9ACD32/?text=+)  |
| Nemuro Main Line (Shintoku~Kushiro)     | K  | 109     | #9ACD32 | ![yellowgreen](https://via.placeholder.com/12/9ACD32/?text=+)  |
| Nemuro Main Line (Takikawa~Shintoku)    | T  | 110     | #FFB6C1 | ![lightpink](https://via.placeholder.com/12/FFB6C1/?text=+)    |
| Senmō Main Line                         | B  | 111     | #FF69B4 | ![hotpink](https://via.placeholder.com/12/FF69B4/?text=+)      |
| Sōya Main Line                          | W  | 112     | #A52A2A | ![brown](https://via.placeholder.com/12/A52A2A/?text=+)        |
| Gakuentoshi Line                        | G  | 113     | #2E8B57 | ![seagreen](https://via.placeholder.com/12/2E8B57/?text=+)     |
| Furano Line                             | F  | 114     | #9370DB | ![mediumpurple](https://via.placeholder.com/12/9370DB/?text=+) |
| Nemuro Main Line (Kushiro~Nemuro)       |    | 115     | #808080 | ![grey](https://via.placeholder.com/12/808080/?text=+)         |
| Muroran Main Line (Tomakomai~Iwamizawa) |    | 116     | #808080 | ![grey](https://via.placeholder.com/12/808080/?text=+)         |
| Hidaka Main Line                        |    | 117     | #808080 | ![grey](https://via.placeholder.com/12/808080/?text=+)         |
| Rumoi Main Line                         |    | 118     | #808080 | ![grey](https://via.placeholder.com/12/808080/?text=+)         |
| South Hokkaido Railway                  | sh | 119     | #000000 | ![black](https://via.placeholder.com/12/000000/?text=+)        |
| 2×× reserved for bus replacement service|    |         |         |                                            |
| Lilac                                   | A  | 301     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Kamui                                   | A  | 302     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Okhotsk                                 | A  | 303     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Taisetsu                                | A  | 304     | #FFA500 | ![orange](https://via.placeholder.com/12/FFA500/?text=+)       |
| Sōya                                    | W  | 305     | #A52A2A | ![brown](https://via.placeholder.com/12/A52A2A/?text=+)        |
| Sarobetsu                               | W  | 306     | #A52A2A | ![brown](https://via.placeholder.com/12/A52A2A/?text=+)        |
| Ōzora                                   | K  | 307     | #9ACD32 | ![yellowgreen](https://via.placeholder.com/12/9ACD32/?text=+)  |
| Tokachi                                 | K  | 308     | #9ACD32 | ![yellowgreen](https://via.placeholder.com/12/9ACD32/?text=+)  |
| Hokuto                                  | H  | 309     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Suzuran                                 | H  | 310     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |
| Furano Lavender Express                 | T  | 311     | #FFB6C1 | ![lightpink](https://via.placeholder.com/12/FFB6C1/?text=+)    |
| Niseko                                  | H  | 312     | #4169E1 | ![royalblue](https://via.placeholder.com/12/4169E1/?text=+)    |


## License
HokkaidoRailGTFS is reeleeased under the MIT License.
For full text see the `license.md` file.
