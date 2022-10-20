import numpy as np
import os
import pandas as pd
import urllib.request
import zipfile

alexa_domains = [
    "google",
    "youtube",
    "tmall",
    "qq",
    "baidu",
    "sohu",
    "facebook",
    "taobao",
    "jd",
    "amazon",
    "yahoo",
    "wikipedia.org",
    "weibo",
    "sina.com.cn",
    "zoom.us",
    "http://www.xinhuanet.com",
    "live",
    "reddit",
    "netflix",
    "microsoft",
    "instagram",
    "office",
    "!panda.tv",
    "zhanqi.tv",
    "alipay",
    "bing",
    "csdn.net",
    "vk",
    "myshopify",
    "naver",
    "okezone",
    "twitch.tv",
    "twitter",
    "ebay",
    "adobe",
    "tianya.cn",
    "huanqiu",
    "yy",
    "aliexpress",
    "linkedin",
    "force",
    "aparat",
    "mail.ru",
    "msn",
    "dropbox",
    "whatsapp",
    "apple",
    "1688",
    "wordpress",
    "canva",
    "indeed",
    "stackoverflow",
    "ok.ru",
    "so",
    "chase",
    "imdb",
    "slack",
    "etsy",
    "tiktok",
    "booking",
    "babytree",
    "rakuten.co.jp",
    "salesforce",
    "spotify",
    "tribunnews",
    "fandom",
    "tradingview",
    "github",
    "haosou",
    "paypal",
    "cnblogs",
    "alibaba",
    "kompas",
    "gome.com.cn",
    "walmart",
    "roblox",
    "6.cn",
    "zillow",
    "godaddy",
    "imgur",
    "espn",
    "bbc",
    "hao123",
    "pikiran-rakyat",
    "grammarly",
    "cnn",
    "telegram.org",
    "tumblr",
    "nytimes",
    "detik",
    "wetransfer",
    "savefrom.net",
    "rednet.cn",
    "freepik",
    "ilovepdf",
    "daum.net",
    "pinterest",
    "primevideo",
    "intuit",
    "medium"
]

if not os.path.exists("top-1m.csv"):
    urllib.request.urlretrieve("http://s3.amazonaws.com/alexa-static/top-1m.csv.zip", "top-1m.csv.zip")

    with zipfile.ZipFile("top-1m.csv.zip") as z:
        z.extractall()

existing_domains = domains = [f"{x.replace('!', '')}{'.com' if '.' not in x else ''}" for x in alexa_domains]
existing_names = set([x.replace("!", "").split(".")[0] for x in alexa_domains])

open_world_domains = []

df = pd.read_csv("top-1m.csv", header=None, names=["rank", "domain"])

for i in range(len(df)):
    domain = df.iloc[i]["domain"]

    if domain in existing_domains:
        continue
    elif domain.split(".")[0] in existing_names:
        continue
    else:
        open_world_domains.append(domain)
        existing_names.add(domain.split(".")[0])
    
    # Provide extra sites (we only need 5000) in case some sites have errors
    if len(open_world_domains) == 6000:
        break

pd.Series(open_world_domains).to_csv("open_world.csv", header=["domain"], index=False)
