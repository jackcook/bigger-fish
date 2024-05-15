# There’s Always a Bigger Fish 🎣

Code from the paper “There’s Always a Bigger Fish: A Clarifying Analysis of a Machine-Learning-Assisted Side-Channel Attack”

## Setup

### Install dependencies

Make sure you have Python 3 installed. Then, install our dependencies.

```
pip install -r requirements.txt
```

### Install browser drivers

You only need to install the drivers for the browsers you would like to use.

- Chrome: Download [here](https://googlechromelabs.github.io/chrome-for-testing/) and add `chromedriver` to your path
- Firefox: Download [here](https://github.com/mozilla/geckodriver/releases) and add `geckodriver` to your path
- Safari: Skip this step! `safaridriver` is built into macOS
- [Tor Browser](https://www.torproject.org): Install [tor-browser-selenium](https://github.com/webfp/tor-browser-selenium)
- [Links](<https://en.wikipedia.org/wiki/Links_(web_browser)>): We didn’t keep any experiments with this text-based browser for the paper, but on macOS you can install it with `brew install links` and use our built-in driver

## Usage

Our recording script takes many command-line arguments, making a wide variety of experiments possible. Most experiments we ran in the paper should be covered here, and you can also create your own experiments by modifying the arguments or changing the attacker code in `attacker/worker.js`.

1. [Basic recording setup](https://github.com/jackcook/bigger-fish/wiki/Basic-recording-setup) (Table 1)
   1. [Adding countermeasures](https://github.com/jackcook/bigger-fish/wiki/Basic-recording-setup#adding-countermeasures) (Table 2)
   2. [Tor Browser experiments](https://github.com/jackcook/bigger-fish/wiki/Basic-recording-setup#using-older-versions-of-chrome)
   3. [Using older versions of Chrome](https://github.com/jackcook/bigger-fish/wiki/Basic-recording-setup#using-older-versions-of-chrome)
   4. [Setting up SMS notifications](https://github.com/jackcook/bigger-fish/wiki/Basic-recording-setup#setting-up-sms-notifications)
2. Isolation experiments (Table 3)
   1. Pin attacker and victim to separate cores
   2. Isolate interrupts from attacker core
3. eBPF analysis tool (Figure 5)
4. Changing timer parameters (Table 4)

## Evaluation

Once you’ve collected some data, you’ll want to train a model and test it to find its accuracy. For small experiments, we’ve included a script, `check_results.py`, that trains a simple random forest model for a quick sanity check.

```bash
# Record 40 5-second traces of the top 4 websites according to Alexa, and
# save the traces to readme-experiment
$ python record_data.py --num_runs 40 --trace_length 5 --sites_list alexa4 --out_directory readme-experiment
...
100%|█████████████████████████████████████████| 160/160 [14:17<00:00,  5.36s/it]

# Load the traces and check accuracy
$ python scripts/check_results.py --data_file readme-experiment
Analyzing results from readme-experiment
100%|███████████████████████████████████████████| 10/10 [00:01<00:00,  5.83it/s]

Number of traces: 160

top1 accuracy: 87.3% (+/- 6.8%)
top5 accuracy: 100.0% (+/- 0.0%)
```

For larger experiments, you’ll want to train an LSTM, as we do in the paper. For ease of use, we’ve included our training code in a Colab notebook: https://colab.research.google.com/drive/1GRQwuxlfoCPaiM7BiP9giHS2sMppvYHH?usp=sharing.

## FAQs

### How should I cite this work?

Please use the following BibTeX entry:

```
@inproceedings{cook2022biggerfish,
    author = {Cook, Jack and Drean, Jules and Behrens, Jonathan and Yan, Mengjia},
    title = {There's Always a Bigger Fish: A Clarifying Analysis of a Machine-Learning-Assisted Side-Channel Attack},
    year = {2022},
    publisher = {Association for Computing Machinery},
    url = {https://doi.org/10.1145/3470496.3527416},
    doi = {10.1145/3470496.3527416},
    booktitle = {Proceedings of the 49th Annual International Symposium on Computer Architecture},
    pages = {204–217}
}
```

## License

This repository is available under the MIT license. See the [LICENSE](/LICENSE.md) file for more details.
