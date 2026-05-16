# Setup — No API keys needed

## 1. Push to GitHub
```bash
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/YOUR_USERNAME/ebay-retro-deals
git push -u origin main
```

## 2. Enable GitHub Pages
1. Go to your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/ (root)`
4. Save

## 3. Run it
- Go to **Actions tab** → click the workflow → **Run workflow** (manual test)
- After it runs, `feed.xml` appears in your repo
- Your RSS feed URL will be:
  ```
  https://YOUR_USERNAME.github.io/ebay-retro-deals/feed.xml
  ```

## 4. Subscribe
Paste that URL into any RSS reader:
- **Feedly** (free, web + mobile)
- **Inoreader** (free)
- Windows 11 Mail app supports RSS
- iPhone: **NetNewsWire** (free)

## How it works
- Runs every day at 9am EST automatically (no server needed)
- Scrapes eBay for newly listed Buy It Now items under price thresholds
- Appends your affiliate params (`campid=5338637261`) to every link
- Commits `feed.xml` to your repo — GitHub Pages serves it instantly
