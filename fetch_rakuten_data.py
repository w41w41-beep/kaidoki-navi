import requests
import json
import os

# GitHub ActionsのシークレットからAPIキーを取得
app_id = os.environ.get('RAKUTEN_API_KEY')
keyword = '家電'
url = f"https://app.rakuten.co.jp/services/api/IchibaItem/Search/20170706?applicationId={app_id}&keyword={keyword}"

response = requests.get(url)
data = response.json()

# 取得したデータをJSONファイルとして保存
with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("APIからデータを取得し、data.jsonに保存しました。")
