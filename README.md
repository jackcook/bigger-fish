# \#722 Reproducing and analyzing side-channel attacks
## Usage
Clone the repo:
```
git clone git@github.com:aliparlakci/bigger-fish.git
```

Run the server that will provide the spyware webpage
```
py -3.11 -m flask --app attacker_server run --port 7777
```

Make experiments:
```
py -3.11 main.py --out_dir .\data --codecs mp4, mkv, flv, 3gp --browsers chrome, edge, safari, firefox --players mplayer, vlc, mpv --samples 100 --len 15
```

Evaluate findings:
```
py -3.11 evaluate.py .\data --targets codec, browser, player --relax user
```
