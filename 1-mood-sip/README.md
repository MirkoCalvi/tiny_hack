# MoodSip - Sip Your Stress Away 🌟

![Logo](./assets/logo.png)

A [video presentation can be seen here](https://youtu.be/YI3l9gEI9GM).

**MoodSip** is a smart water bottle developed by **[@pitadagosti](https://github.com/pitdagosti), [@davmacario](https://github.com/davmacario), and [@FrigaZzz](https://github.com/frigazzz)**.
It integrates an **Arduino Nicla Vision** to adapt your hydration rhythm to your needs, combining **water tracking** and **emotion detection** 💆.

Studies show that even mild dehydration can reduce concentration, cause fatigue, and irritability [1]. Proper hydration can reduce cortisol spikes under stress [2] and improve physical and mental well-being.

MoodSip helps you **drink smarter and manage stress**, promoting both physical and mental health.

## Hydration Matters 💧

Fluid loss negatively affects the body:

- **Common symptoms:** fatigue, confusion, reduced physical and mental performance
- **Elderly:** dehydration is widespread, increasing mortality and healthcare costs
- **Stress:** even mild water deprivation amplifies stress response with higher cortisol peaks

Benefits of proper hydration:

- Prevents headaches
- Reduces fatigue
- Improves skin and cognitive performance

Technology can support regular hydration habits. Current smart bottles remind you to drink and track intake, but rarely consider **emotional state**. MoodSip fills this gap with a **holistic daily wellness approach**.

---

## Existing Solutions 🤖

**HidrateSpark PRO**

- SipSense sensors weigh the bottle and track every sip
- Bluetooth app with personalized goals
- Bottle lights up when it’s time to drink
- Focus: quantitative hydration tracking

**REBO SMART**

- Tracks personalized hydration via Bluetooth and app
- Environmental impact: "1 REBO drank = 1 plastic bottle collected from oceans"
- Digital reminders and hydration plans based on activity and body

**Limitations:**

- Most focus on **water quantity and notifications**
- None integrate **emotion detection**

MoodSip bridges this gap by combining **hydration tracking** and **mood sensing** for a personalized experience.

---

## How MoodSip Works 🌡️😊

MoodSip runs an **adaptive timer** based on:

### 1. Facial Expressions (Stress)

- **Nicla Vision camera** captures the user’s face
- ML model (FocoosAI) detects signs of stress (e.g., furrowed brows, tired eyes)
- If stress is detected, the LED turns **red 🔴** and the drinking reminder accelerates

### 2. Ambient Temperature

- Sensor measures temperature and humidity
- In hot or humid conditions, the timer shortens to encourage more frequent drinking

### 3. Drinking Duration

- LED turns **blue 🔵** when it’s time to drink
- Proximity and gyroscope sensors estimate water intake
- If intake is low, the next timer is shortened to encourage proper hydration

**Summary:** MoodSip continuously adapts drinking reminders based on stress, temperature, and actual water intake. Everything runs on **Arduino Nicla Vision**, completely offline.

---

## Technologies ⚙️

- **Arduino Nicla Vision:** 2MP camera, proximity sensors, 6-axis gyroscope/accelerometer, Wi-Fi/BLE
- **Focoos AI:** computer vision library for facial expression recognition
- **Z-Ant:** open-source framework to optimize neural models on microcontrollers

**Advantage:** onboard intelligence, portable, and fully offline.

---

## Fun Mode 🎲🍺

MoodSip can turn into a **party drinking game**:

- Everyone keeps a poker face
- Camera detects smiles or other emotions
- **Red LED 🔴** lights up for the “caught” person → that player takes a sip

Uses the same emotion detection mechanism for fun and social interaction.

---

## Impact & Benefits 👍🏼

MoodSip is more than a gadget:

- **Promotes public health:** encourages hydration and stress management
- Supports elderly, professionals, and athletes
- Raises awareness of mind-body connection: drinking water can relieve mental tension

Compared to other smart bottles, MoodSip is more **holistic**: it doesn’t just count milliliters—it “understands” the user.
Potentially reduces dehydration-related medical visits and improves daily life and performance.

---

## Technical overview

For the technical overview, see [here](./docs/software.md).

---

## References 📚

[1]. Dehydration: the enemy of our body](<https://medimutua.org/disidratazione-il-nemico-del-nostro-organismo/>)
[2]. [Trends in Dehydration in Older People](https://www.mdpi.com/2072-6643/17/2/204) 3. **This Simple Everyday Health Tweak Can Help Reduce Anxiety And Future Health Problems** 4. **5 Best Smart Water Bottles of 2024**

Existing product references: **HidrateSpark**, **REBO** → measure water intake but not emotions. MoodSip does both: **sip your stress away!** 🌊
