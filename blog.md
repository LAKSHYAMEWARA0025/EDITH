# EDITH: Teaching an AI to Command Drones Like EDITH- Tony Stark's AI Drone System

*Built for OpenEnv Hackathon — India 2026 | Theme: Multi-Agent Interactions + World Modeling*

---

## It Started With a Movie Scene

Let's be real — most of us didn't get into tech because of textbooks. It was movies.

For us, it was Tony Stark.

Not the billionaire part (unfortunately). The *engineering genius* part. The idea that you could build something that doesn't just execute commands — it *thinks*, adapts, and decides.

There's this scene in *Spider-Man: Far From Home* where EDITH — Tony's AI connected to his smart glasses — commands an entire drone swarm with surgical precision. The drones moved as one unit, dodging threats, reassigning targets, executing a complex mission without a single manual input.

That's not automation. That's intelligence.

And somewhere between watching that scene and seeing the hackathon announcement, the question hit us:

**What if we trained an AI to actually do that?**

---

## The Big Idea (In Plain English)

Most drones today aren't "smart." They follow a script — if obstacle detected, turn left; if battery low, return home(kind of hardcode). Great for predictable conditions. Terrible for anything real-world and messy.

We wanted to build something different: an AI that *reasons* about a mission, makes decisions, and gives instructions like a commander would.

Not "spin motor 3 at 40% RPM."

More like:

- *"Scan that zone before you move through it."*
- *"Drone 2, reroute — there's an obstacle to the north."*
- *"Battery's at 20%, abort and return home."*

Think of it as:

> **AI = The brain (mission commander)**
>  **Drone = The body (executes the orders)**

The AI never touches the flight physics. A separate controller handles that. The AI just decides *what to do* — and that turns out to be a genuinely hard problem.

---

## How We Split the Work

There were just two of us, and a 24-hour clock ticking.

**One handled the "brain side":**
- Designing the tasks and missions
- Building the reward system (how the AI learns what "good" means)
- Writing the tool functions the AI could call
- Physics simulation integration, battery modeling, API layer

**Other handled the "environment side":**
- Finding the right drone simulation library
- Building the OpenEnv wrapper and FastAPI server
- Action and observation models — the interface between the AI and the drone world

We weren't just writing code. We were building a **miniature world where an AI could learn to fly drones**.

---

## Day 1: The Wall We Hit First

We started strong. We had the idea, we had the energy, and we had **PySimverse** — a Python library with a full 3D Unity engine for drone simulation. It looked perfect on paper.

Then the first real problem showed up: we needed to package everything for deployment.

PySimverse looked perfect — a Python library with a 3D simulation engine. But it had a critical flaw: the engine only worked on Mac and Windows. Our deployment needed to run on Linux servers. No workaround existed. It was like trying to run an iPhone app on an Android phone — fundamentally incompatible.

On top of that, the engine needed a screen to display graphics. Server environments don't have screens. And there was another issue: AI models take 1-2 seconds to think. Drones need instant commands. The timing just didn't work.

We had to pivot. Fast.

---

## The Pivot That Saved the Project

We switched to **gym-pybullet-drones** — a research-grade physics engine built for AI training. It runs without needing a screen, works on Linux, and is lightweight enough for basic hardware.

That single switch unblocked everything.

But we also had to rethink something more fundamental: **what role should the AI actually play?**

Our original instinct was to make the AI control every tiny detail — like telling the drone exactly how fast to spin each motor. That's too fast and too detailed for an AI that needs time to think.

So we flipped it. We made the AI a **strategic mission commander** instead.

The AI doesn't control motors. It makes high-level decisions like:

| Tool | What it does |
|------|-------------|
| `get_obstacle_distances()` | Scans surroundings and returns obstacle proximity |
| `move_drone(x, y, z)` | Commands the drone to a specific coordinate |
| `assign_drone_to_target(drone_id, target)` | Sends a drone to a mission objective |
| `get_battery_status()` | Checks remaining battery level |
| `return_home(drone_id)` | Recalls a drone back to base |

A PID controller handles the actual flight physics underneath. The AI handles the *strategy* on top. This separation is what made the whole system trainable — and is exactly how EDITH works.

---

## Building the Environment (The Unglamorous Part)

Even after switching libraries, the next few hours were brutal in ways no tutorial prepares you for.

Installing PyBullet required a C++ compiler. Dependency conflicts appeared out of nowhere. Integration between the physics engine, the OpenEnv wrapper, and the API layer kept breaking in creative new ways.

But we pushed through. After grinding through the build, the debugging, and some late-night calls, we had a working environment. Time to actually test it.

---

## The First Test: Beautiful Disaster

After building the complete integrated environment, we wanted to test it against a real LLM. We used the HuggingFace API with **Qwen2.5-72B-Instruct** — a massive, capable model. The task was simple: find the target by searching the area, avoid obstacles, reach it, return home.

Even with a 72B parameter model, the agent struggled. Badly.

And then the real debugging began.

### Challenge 1: The Camera That Looked at the Ground

The drone had a camera to detect obstacles and targets. But it wasn't working. The camera was pointing straight down at the ground instead of forward. We fixed the angle, and suddenly the drone could "see" what was ahead.

### Challenge 2: Confused Directions

The drone kept moving in the wrong direction. If the target was north, it would fly east. The problem was how the drone understood directions — its internal compass was getting confused. We gave it a fixed reference system so it always knew which way was which.

### Challenge 3: The Wandering Drone

The drone kept flying farther and farther away, searching for the target. We set boundaries — invisible walls the drone couldn't cross. This forced it to search smarter, not just wander endlessly.

### Challenge 4: The Task Was Too Hard

Even a powerful AI model struggled. Why? Because AI models are trained on text, code, and conversations — not flying drones. They don't naturally know "scan before you move" or "check your battery."

We realized we needed to teach the AI step by step.

### Making Learning Possible

We redesigned how the AI learns. Instead of only getting feedback at the very end (success or failure), we gave it feedback at every step:

- Moving closer to the target? Small reward.
- Hitting an obstacle? Penalty.
- Scanning before moving? Bonus points.

This way, the AI could learn from every action, not just the final outcome.

We also simplified the first task. Instead of making the drone search for the target, we told it where the target was. The challenge became: "Can you navigate there without crashing?" Once it learns that, we can add more complexity.

### The Obstacle Problem

At first, obstacles were placed randomly. Sometimes they blocked the path, sometimes they didn't. The AI couldn't learn a consistent strategy.

We changed the algorithm to place obstacles intentionally along the path to the target. Now every episode was challenging, and the AI had to learn to scan, detect obstacles, and find alternate routes.

That's how RL works. You don't tell the agent what to do. You let it fail, and the reward signal teaches it what worked and what didn't.

---

## The Training Plan: Curriculum Learning

We designed a curriculum — the same principle behind how humans learn: master the easy stuff first, then tackle harder problems, carrying your knowledge forward.

**Task 1 — Easy:** Single drone, static obstacles, simple navigation. Get from A to B without crashing.

**Task 2 — Medium:** Add battery management and moving obstacles.

**Task 3 — Hard:** Two drones working together as a team.

### How We Trained the AI

We used a step-by-step approach called "curriculum learning" — like how you learn math by starting with addition before moving to calculus.

First, we trained the AI on the easiest task until it got good at it. Then we saved what it learned and used that as a starting point for the next, harder task. This way, the AI builds on what it already knows instead of starting from scratch each time.

Think of it like learning to drive: first you practice in an empty parking lot, then on quiet streets, then on highways. Each step builds on the previous one.

We deployed our training on Google Colab with computing credits from the hackathon and started the training process.

---

## Generation 1: The Struggle

The first training run was rough. We gave it 50 episodes to learn from. The reward curve oscillated wildly. The agent couldn't figure out tool sequencing. It would scan once, then never again. It moved blindly into obstacles. Loss barely decreased.

**Easy Task mean reward: ~0.05 out of 1.0**

The agent was learning *something* — it stopped calling completely invalid tools — but it wasn't learning *strategy*. It wasn't connecting "scan before you move" with "higher reward."

Here's the thing: 50 episodes isn't much. For a small model like Qwen 1.5B learning drone navigation from scratch, you need *hundreds* of episodes to see enough successful trajectories. The agent needs to stumble into a good outcome by chance a few times before GRPO can recognize the pattern and reinforce it.

We were running out of time.

---

## Generation 2: Something Clicked

We took the Gen 1 weights and trained again on the same task. This time, things started to shift.

The oscillation reduced. The agent started calling `get_obstacle_distances()` more consistently. It began routing around obstacles instead of through them. The reward curve climbed — slowly, but it climbed.

**Easy Task mean reward: ~0.35 out of 1.0**

Still not where we wanted. The agent would scan, then sometimes ignore the data anyway. It'd detect an obstacle to the north and still try to fly north. But the trend was undeniable — it was learning. Tool call patterns were improving. The curve was going up.

The improvement was clear: **7x reward increase** from Gen 1 to Gen 2 (0.05 → 0.35). The AI was getting better at understanding how to navigate.

We ran out of time before Gen 3. But we could see exactly where it was heading.

---


## What We Actually Learned

### 1. Test your tools early
PySimverse looked perfect on paper. But it couldn't run on the servers we needed. Always test compatibility before building your entire project around a tool.

### 2. AI doesn't naturally know how to fly drones
Even powerful AI models struggle with drone navigation because they're trained on text and code, not physical movement. Teaching an AI to fly requires starting from scratch with lots of practice.

### 3. Give feedback at every step
Our first attempt only told the AI "success" or "failure" at the end. That's not enough. We changed it to give small rewards or penalties after every action. This helped the AI learn much faster.

### 4. Start simple, then add complexity
We tried to make the AI do everything at once and it failed. When we broke it into smaller steps (first learn to navigate, then add battery management, then add multiple drones), it started working.

### 5. Simulation without graphics is essential
We needed the drone simulation to run on servers without screens. PyBullet's headless mode made this possible. Without it, we couldn't have trained or deployed anything.

### 6. Building is harder than planning
We spent more time fixing bugs and edge cases than writing the actual AI code. That's normal in real projects — the unexpected problems take the most time.

---

## What Comes Next

If we had more time and computing power, here's what we'd do:

- **Continue training** until the AI consistently completes the basic navigation task
- **Add harder challenges** like limited battery and moving obstacles
- **Train multiple drones** to work together as a team
- **Test on new scenarios** the AI has never seen before to prove it really learned, not just memorized

The foundation is built. The AI is learning. We just need more time to see it reach its full potential.

---

## Why This Matters

Today's drone swarms follow pre-programmed instructions. They work great — until something unexpected happens. A drone runs out of battery. An obstacle appears. The mission changes mid-flight. Scripts can't handle that.

We're building something different: drones that can think, adapt, and make decisions in real-time. Drones that can handle the unexpected.

This has real applications: disaster response, search and rescue, infrastructure inspection, delivery systems. Anywhere you need drones to operate in unpredictable environments.

We didn't finish everything in 24 hours. But we proved the concept works and built the foundation to take it further.

---

## Links

### Project Links
- **Environment:** https://huggingface.co/spaces/Invictus-Jai/edith-mission-commander
- **Training Code:** https://colab.research.google.com/drive/1YEFLDpLOA14hsdkyqs4fQMd3qK-Pbnmt

### Dependencies & Resources
- **gym-pybullet-drones (GPD):** https://github.com/utiasDSL/gym-pybullet-drones.git
- **PySimverse Website:** https://pysimverse.com
- **PySimverse Tutorial:** https://youtu.be/hedBZ_ViAGo?si=y2KjPuXtTts2pb4p

---

*Built with chaos. Built with curiosity. Built to keep going.*
### Team Troopers, Signing Off!