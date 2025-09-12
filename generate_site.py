name: Generate and Deploy Site

on:
  schedule:
    # 毎日午前10時 (UTC)に実行
    - cron: '0 1 * * *' 
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.x'

      - name: Install dependencies (if needed)
        run: |
          python -m pip install --upgrade pip
          # ここに将来的に必要なライブラリのインストールコマンドを追加

      - name: Run Python script
        run: python generate_site.py

      - name: Commit and Push changes
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add index.html
          git commit -m "Auto-generated site update" || echo "No changes to commit"
          git push
