# 📱 APK Refer & Earn Bot

A Telegram bot where users earn points by referring friends and redeem them for APKs — fully automatic delivery.

---

## 🚀 Deploy on Render — Step by Step

### 📌 Step 1 — Free Database Banao (Neon.tech)
> Render pe already ek database hai, isliye alag free database use karenge

1. **[neon.tech](https://neon.tech)** → Sign up (Google se bhi ho jaata hai)
2. **"New Project"** → koi bhi naam → **"Create"**
3. **"Connection string"** copy karo — kuch aisa dikhega:
   `postgresql://user:pass@ep-xxx.neon.tech/neondb`
4. Is string ko save kar lo

---

### 📌 Step 2 — Bot Token & Admin ID Lo
- **[@BotFather](https://t.me/BotFather)** → `/newbot` → **Token** copy karo
- **[@userinfobot](https://t.me/userinfobot)** → `/start` → **ID** copy karo

---

### 📌 Step 3 — Render Blueprint Deploy
1. **[render.com](https://render.com)** → Login
2. **"New +"** → **"Blueprint"**
3. **`apk-refer-earn-bot`** repo select karo
4. Render 3 variables puchega — fill karo:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | BotFather wala token |
| `ADMIN_ID` | Tera Telegram ID |
| `DATABASE_URL` | Neon.tech wali connection string |

5. **"Apply"** → Deploy! ✅

> `RENDER_URL` automatically set ho jaata hai — kuch karna nahi!

---

## ⚙️ Bot Setup (Deploy ke Baad)

1. `/admin` → Admin panel
2. **📡 Channels** → **➕ Add Channel**
3. **📱 APK Manager** → **➕ Add APK** (naam → password → points)
4. `/setreward 1` → referral reward set karo

---

## 📋 Admin Commands

| Command | Description |
|---|---|
| `/admin` | Admin panel |
| `/setreward N` | Referral reward set karna |
| `/block USER_ID` | User block karna |
| `/unblock USER_ID` | User unblock karna |
| `/addpts USER_ID N` | Points add karna |
| `/rmpts USER_ID N` | Points hatana |
| `/userinfo USER_ID` | User details dekhna |

---

## 🌟 Features

- ✅ **Force Join** — channels join karne ke baad hi access
- 🎯 **Referral System** — refer karo, points kamao
- 📱 **APK Redemption** — automatic naam + password delivery
- 🛡 **Admin Panel** — full inline button control
- 📢 **Broadcast** — users ya channels ko message
- ⏰ **Keep-Alive** — har 10 min auto ping, free tier pe bhi 24/7 online
