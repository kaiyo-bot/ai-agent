# 🤖 6 Lottery AI Agent Predictor

Termux မှာ run လို့ရတဲ့ Node.js Telegram bot project ပါ။

## 🎮 Included
- 🟢 6 Lottery Wingo 1 Min
- 🔴 6 Lottery TRX
- 🔐 6 Lottery Phone + Password login
- 🆔 Game ID ကို GetUserInfo ကနေ စစ်ခြင်း
- 👑 Admin-approved Game IDs
- 📊 Wingo/TRX သီးခြား 1700 history
- 🔄 Live history auto update
- 🎯 old → new input (`0,2`)
- 📈 0–9 %, BIG/SMALL %
- 🔎 Level 1/2/3 statistical prediction
- ✅ WIN / ❌ LOSE inline buttons
- 👑 Admin Panel: Add User / Remove User / Broadcast / Allowed IDs / Main Menu
- 🎨 Emoji ကို config ကနေ Custom/Premium Emoji ID ထည့်နိုင်ပြီး blank ထားရင် Unicode fallback သုံးမယ်

## 📱 Termux
1. Zip ကို extract လုပ်ပါ။
2. Project folder ထဲဝင်ပါ။
3. `cp .env.example .env`
4. `.env` ထဲမှာ BOT_TOKEN, ADMIN_CHAT_ID, ADMIN_USERNAME ဖြည့်ပါ။
5. `npm install`
6. `npm start`

## ⚠️ Important
- API response field တွေက 6 Lottery endpoint အပြောင်းအလဲရှိရင် `extractResult()` ကို ပြင်ရနိုင်ပါတယ်။
- Bot က betting order မပို့ပါ။ Prediction/statistics ပဲလုပ်ပါတယ်။
- Result/Period ကို API history/current-issue endpoint ကနေယူဖို့ရေးထားပါတယ်။
- Native Telegram Reply Keyboard ရဲ့ background color ကို bot က arbitrary hex နဲ့ မသတ်မှတ်နိုင်ပါ။ Emoji/icon နဲ့ label ကို သတ်မှတ်ထားပါတယ်။
- Custom emoji IDs ကို `.env` ထဲထည့်နိုင်ပါတယ်။ ID မထည့်ထားရင် bot မပျက်ဘဲ Unicode fallback သုံးပါမယ်။


## 🎨 Custom/Premium Emoji
`.env` ထဲမှာ ဥပမာ `CUSTOM_EMOJI_WIN=1234567890123456789` လို့ ID ထည့်ပါ။
ID ကို message text ထဲမှာ နံပါတ်အဖြစ် မပြဘဲ Telegram `<tg-emoji>` entity နဲ့ render လုပ်ပေးထားပါတယ်။
Button တွေမှာတော့ `icon_custom_emoji_id` field ကို သီးခြားသုံးထားပါတယ်။
Bot owner မှာ Telegram Premium ရှိခြင်း (သို့) Fragment additional usernames requirement စတဲ့ Telegram eligibility rules တွေ သက်ရောက်နိုင်ပါတယ်။
