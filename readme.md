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


| Line Name                          | JR Code | GTFS ID | Color | Color Example                            |
|-----------------------------------------|----|-----|---------|--------------------------------------------|
| Hakodate Main Line (Hakodate~Oshamambe) | H  | 100 | #4169E1 | <span style="color: royalblue;">■</span>   |
| Muroran Main Line (Oshamambe~H-Muroran) | H  | 101 | #4169E1 | <span style="color:royalblue;">■</span>    |
| Muroran Main Line (H-Muroran~Tomakomai) | H  | 102 | #4169E1 | <span style="color:royalblue;">■</span>    |
| Chitose Line                            | H  | 103 | #4169E1 | <span style="color:royalblue;">■</span>    |
| Hakodate Main Line (Otaru~Sapporo)      | S  | 104 | #FF0000 | <span style="color:red;">■</span>          |
| Hakodate Main Line (Sapporo~Asahikawa)  | A  | 105 | #FFA500 | <span style="color:orange;">■</span>       |
| Hakodate Main Line (Oshamambe~Otaru)    | S  | 106 | #FF0000 | <span style="color:red;">■</span>          |
| Sekihoku Main Line                      | A  | 107 | #FFA500 | <span style="color:orange;">■</span>       |
| Sekishō Line                            | K  | 108 | #9ACD32 | <span style="color:yellowgreen;">■</span>  |
| Nemuro Main Line (Shintoku~Kushiro)     | K  | 109 | #9ACD32 | <span style="color:yellowgreen;">■</span>  |
| Nemuro Main Line (Takikawa~Shintoku)    | T  | 110 | #FFB6C1 | <span style="color:lightpink;">■</span>    |
| Senmō Main Line                         | B  | 111 | #FF69B4 | <span style="color:hotpink;">■</span>      |
| Sōya Main Line                          | W  | 112 | #A52A2A | <span style="color:brown;">■</span>        |
| Gakuentoshi Line                        | G  | 113 | #2E8B57 | <span style="color:seagreen;">■</span>     |
| Furano Line                             | F  | 114 | #9370DB | <span style="color:mediumpurple;">■</span> |
| Nemuro Main Line (Kushiro~Nemuro)       |    | 115 | #808080 | <span style="color:grey;">■</span>         |
| Muroran Main Line (Tomakomai~Iwamizawa) |    | 116 | #808080 | <span style="color:grey;">■</span>         |
| Hidaka Main Line                        |    | 117 | #808080 | <span style="color:grey;">■</span>         |
| Rumoi Main Line                         |    | 118 | #808080 | <span style="color:grey;">■</span>         |
| South Hokkaido Railway                  | sh | 119 | #000000 | <span style="color:black;">■</span>        |
| 2×× reserved for bus replacement service|    |     |         |                                            |
| Lilac                                   | A  | 301 | #FFA500 | <span style="color:orange;">■</span>       |
| Kamui                                   | A  | 302 | #FFA500 | <span style="color:orange;">■</span>       |
| Okhotsk                                 | A  | 303 | #FFA500 | <span style="color:orange;">■</span>       |
| Taisetsu                                | A  | 304 | #FFA500 | <span style="color:orange;">■</span>       |
| Sōya                                    | W  | 305 | #A52A2A | <span style="color:brown;">■</span>        |
| Sarobetsu                               | W  | 306 | #A52A2A | <span style="color:brown;">■</span>        |
| Ōzora                                   | K  | 307 | #9ACD32 | <span style="color:yellowgreen;">■</span>  |
| Tokachi                                 | K  | 308 | #9ACD32 | <span style="color:yellowgreen;">■</span>  |
| Hokuto                                  | H  | 309 | #4169E1 | <span style="color:royalblue;">■</span>    |
| Suzuran                                 | H  | 310 | #4169E1 | <span style="color:royalblue;">■</span>    |
| Furano Lavender Express                 | T  | 311 | #FFB6C1 | <span style="color:lightpink;">■</span>    |
| Niseko                                  | H  | 312 | #4169E1 | <span style="color:royalblue;">■</span>    |


## License
HokkaidoRailGTFS is reeleeased under the MIT License.
For full text see the `license.md` file.
