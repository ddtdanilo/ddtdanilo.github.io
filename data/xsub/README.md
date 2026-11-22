# X-Sub board layout

The public [Altium board](https://github.com/X-Sub/Telemetry-System/blob/22aa3054668b9ac26f78241831455f62f9df0d27/PCB/X-Sub_Board/MCU.PcbDoc) was imported with KiCad 10. The original layout and this copy are distributed under the included [MIT license](LICENSE).

```sh
kicad-cli pcb import --format altium -o data/xsub/mcu.kicad_pcb Telemetry-System/PCB/X-Sub_Board/MCU.PcbDoc
python3 tools/build_site.py
python3 tools/build_site.py --check
```

The site generator reads the imported layout with the Python standard library. It writes `assets/img/hero-board.svg` and `assets/img/board.json`, and inlines the same geometry in the English and Spanish portfolio and X-Sub pages. The JSON retains exact dimensions. Displayed dimensions are rounded to one decimal place.

The figure shows the original traces, pads, vias, outline, and simplified copper pours. It retains board-level silkscreen outlines. Solder paste, solder mask, fabrication marks, and tiny reference text are omitted. Layer spacing and visible edge thickness illustrate the stack.
