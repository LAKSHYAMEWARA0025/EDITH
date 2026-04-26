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

Then the first real problem showed up: we needed to package everything in Docker for submission.

Here's the thing — PySimverse has two components. One is the Python library that controls the drones. The other is a standalone 3D engine built in Unity that handles the physics and rendering. The engine requires its own dedicated launcher app to run. And that launcher? Only available for Mac and Windows. No Linux version.

Docker runs on Linux. That's not a configuration issue you can patch around. It's a fundamental incompatibility. We couldn't even attempt to containerize it — the engine simply wouldn't exist in that environment.

On top of that, the Unity engine had no headless mode — the GUI had to physically render on screen. Even if we somehow got it running on Linux, inside a Docker container there's no display server. Instant crash.

And even setting all of that aside, there was another problem lurking underneath: LLMs have a 1–2 second response time. Drones need *continuous* commands. By the time the AI finished "thinking," the drone would already be inside a wall.

PySimverse was a dead end. We had burned hours on it, and we had to make a call — cut our losses and find something that actually works.

---

## The Pivot That Saved the Project

We switched to **gym-pybullet-drones** — a research-grade physics engine built specifically for reinforcement learning with drones. It runs headless (no display needed), is natively Linux-compatible, fits perfectly inside Docker, and is lightweight enough to run on limited hardware.

That single switch unblocked everything.

But we also had to rethink something more fundamental: **what role should the AI actually play?**

Our original instinct was to make the AI a low-level pilot — sending continuous motor speed commands every few milliseconds. That's too fast, too granular, and honestly not what a language model is good at.

So we flipped it. We made the AI a **strategic mission commander** instead.

The AI gets a set of "tools" it can call — high-level actions like:

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

Our initial Task 1 design required the drone to *find* the target itself using the `scan_area` tool. The agent would call the tool, the camera would capture the scene, and OpenCV would detect the target marker.

Except the camera wasn't working. No matter where the drone moved, `scan_area` returned nothing. We dug into the PyBullet camera setup and found the issue — the camera was facing straight down, perpendicular to the ground, locked in place. The drone was flying around scanning dirt.

We fixed the camera calibration. Now it faced forward.

### Challenge 2: Gimbal Lock

Next problem: the agent started hallucinating movement directions.

If the target was straight ahead along the Y-axis, the drone would move along the X-axis thinking it was going "forward." This is a classic issue called **gimbal lock** — when a 3D rotation system loses a degree of freedom because two axes align. In our case, the drone's internal orientation representation was hitting singularities, causing the coordinate frame to flip unpredictably.

The fix: we explicitly provided the drone with a fixed world coordinate system in the observation. Now the agent knew exactly which axis was which, regardless of the drone's orientation.

### Challenge 3: The Infinite Search

With the camera working and coordinates fixed, the agent started moving. And moving. And moving away from the target.

The world was large. The agent had to search for the target. But it kept drifting farther and farther out, convinced the target must be "just a bit farther." We added a penalty for moving away from the target zone. The agent ignored it and kept searching.

The real fix: we set hard boundary limits. The agent had to search within a defined region. Cross the boundary, instant penalty. The agent learned to stay inside.

### Challenge 4: The Task Was Just Too Hard

Even after fixing all of that, we hit a wall. The agent still couldn't complete the mission consistently.

Here's the thing: LLMs are trained on code, chat, reasoning, problem-solving — not drone flight control. Even a 72B model doesn't have an intuition for "scan before you move" or "check your distance to the obstacle." That's not in its training data.

We realized we were asking too much too soon.

### The Reward System Overhaul

We went back and redesigned the reward function from scratch. The original was too sparse — the agent got almost no signal until the very end of the episode. If it crashed halfway through, it learned nothing about what went wrong.

We built a **two-layer hybrid reward system**:

**Layer 1 — Per-Step Rewards:**  
Every single step, the agent gets feedback. Not for calling the "right" tool, but for making *progress*.

- **Distance signal:** Moving closer to the target? Small positive reward. Moving away? Small negative.
- **Milestone bonuses:** First scan completed? +0.05. Target located? +0.05. Halfway there? +0.10. These fire *once* per episode when thresholds are crossed — no farming allowed.
- **Deviation penalties:** Collision? -0.20. Repeated tool call? -0.05. Battery critical and you're still flying away from home? -0.10.

The agent always has gradient. There's no dead zone where it gets zero signal and learns nothing.

**Layer 2 — Episode-End Rewards:**  
At the end, a comprehensive score based on four components:

- **Mission completion (40%):** Did you reach the targets?
- **Safety (30%):** How many collisions?
- **Efficiency (20%):** How fast did you complete it?
- **Battery (10%):** How much power did you conserve?

The two layers combine into a final normalized score between -1.0 and +1.0. A perfect episode scores near +1.0. An episode where the agent loops doing nothing scores near -0.5. GRPO gets clear, graded signal to learn from.

This structure solved the sparse reward problem. Now the agent could learn incrementally — every step taught it something.

### Simplifying Task 1

We made one more critical change: we gave the agent the target coordinates upfront.

This sounds like cheating, but it's not. The goal of Task 1 isn't "find the target" — it's "learn to navigate to a known point while avoiding obstacles." The agent needs to learn tool sequencing, spatial reasoning, and obstacle avoidance *first*. Once it masters that, we can add the complexity of searching.

Now the agent knew where to go. The challenge was getting there without crashing.

### The Obstacle Placement Problem

The agent started reaching the target. Great. Except now it was *too easy* — it would just call `move_drone_to(target)` and fly straight there in one step.

The problem: our obstacle randomizer was scattering boxes randomly across the scene. Sometimes they blocked the path. Often they didn't. There was no logical structure.

We rewrote the placement algorithm. Now obstacles are placed with intentional offsets along the path between the drone and the target. We increased their height. We added clustering. The obstacles still randomize every episode, but now they *guard* the path. The agent can't just fly straight through. It has to stop, scan, think, and route around.

Now the LLM was sometimes reaching the target — if the path was simple. Otherwise, it crashed into obstacles or the ground.

But that was the point. During training, the agent would see thousands of episodes. It would learn that the episodes where it crashed had one thing in common: it didn't call `get_obstacle_distances()` before moving. Over time, it would learn to scan first.

That's how RL works. You don't tell the agent what to do. You let it fail, and the reward signal teaches it what worked and what didn't.

---

## The Training Plan: Curriculum Learning

We designed a curriculum — the same principle behind how humans learn: master the easy stuff first, then tackle harder problems, carrying your knowledge forward.

**Task 1 — Easy:** Single drone, static obstacles, simple navigation. Get from A to B without crashing.

**Task 2 — Medium:** Add battery pressure. Add moving obstacles. Add mid-mission events that force replanning.

**Task 3 — Hard:** Two-drone coordination. Resource allocation. Swarm strategy.

### Why Curriculum Learning?

Each task is like a level in a game. The agent *must* learn Task 1 before it can handle Task 2. If we trained on all three tasks at once, here's what would happen:

- Task 1 might pass
- Task 2 performs terribly
- Now we have to retrain from scratch — we can't isolate which task broke

With curriculum learning, we train Task 1 until the agent crosses a reward threshold (say, 0.70 mean reward over 50 episodes). Then we save the weights.

For Task 2, we *load* those Task 1 weights as the starting point. The model already knows how to navigate and avoid obstacles. Now it just needs to learn battery management and dynamic obstacle timing. The weights saved after Task 2 training contain learnings from *both* Task 1 and Task 2.

Same for Task 3 — load Task 2 weights, train on swarm coordination, save the final model.

This gives us two huge advantages:

1. **Validation per task** — We can test each task in isolation on a held-out scene. If Task 1 generalizes but Task 2 doesn't, we know exactly where the problem is.

2. **Extensibility** — Want to add Task 4 later? Just load the Task 3 weights and train on the new task. The model carries all previous learnings forward.

The method: train on Task 1 until the agent hits a reward threshold, save the model weights, then use those weights as the starting point for Task 2. Each generation builds on the last — like a student who already knows the basics before tackling the hard exam.

We deployed to Colab with our compute credits and started training.

---

## Generation 1: The Struggle

The first training run was rough. We gave it 50 episodes to learn from. The reward curve oscillated wildly. The agent couldn't figure out tool sequencing. It would scan once, then never again. It moved blindly into obstacles. Loss barely decreased.

**Easy Task mean reward: ~0.05 out of 1.0**

The agent was learning *something* — it stopped calling completely invalid tools — but it wasn't learning *strategy*. It wasn't connecting "scan before move" with "higher reward."

Here's the thing: 50 episodes isn't much. For a small model like Qwen 1.5B learning drone navigation from scratch, you need *hundreds* of episodes to see enough successful trajectories. The agent needs to stumble into a good outcome by chance a few times before GRPO can recognize the pattern and reinforce it.

We were running out of time.

---

## Generation 2: Something Clicked

We took the Gen 1 weights and trained again on the same task. This time, things started to shift.

The oscillation reduced. The agent started calling `get_obstacle_distances()` more consistently. It began routing around obstacles instead of through them. The reward curve climbed — slowly, but it climbed.

**Easy Task mean reward: ~0.35 out of 1.0**

Still not where we wanted. The agent would scan, then sometimes ignore the data anyway. It'd detect an obstacle to the north and still try to fly north. But the trend was undeniable — it was learning. Tool call patterns were improving. The curve was going up.

We ran out of time before Gen 3. But we could see exactly where it was heading.

---

## What We Actually Learned

### 1. Always check library compatibility before you fall in love with it
PySimverse looked like the perfect tool — until we tried to run it on Linux inside Docker. The incompatibility wasn't subtle; it was architectural. Always validate against your deployment environment before you invest hours building on top of something.

### 2. Drone control is genuinely hard for AI
Even a "simple" navigation task requires spatial reasoning, tool sequencing, and multi-step planning. An untrained model has none of this. Every piece has to be learned from scratch — don't underestimate the task just because the concept sounds simple.

### 3. Reward shaping is everything
Our first reward function was too sparse — the agent got almost no signal until the very end of the episode. Adding milestone bonuses for intermediate good behavior was what made training actually converge. If you don't reward the *steps*, the model can't find its way to the *outcome*.

### 4. Curriculum learning works — but needs time
The improvement between Gen 1 and Gen 2 using the same weights was real and measurable. The method works. RL training is just slow. We needed more compute time to see the full curriculum play out.

### 5. Headless simulation is non-negotiable
PyBullet's DIRECT mode (no GUI, no display server, pure physics) was the only reason we could deploy and train at all. If a simulation requires a screen to run, it can't scale. Lesson learned the hard way, but learned well.

### 6. The gap between "works in theory" and "works in practice" is enormous
We spent more time debugging environment edge cases — stuck drones, battery drain bugs, collision detection glitches — than we did on the RL algorithm itself. That's almost always how it goes.

---

## What Comes Next

If we had more time and compute, here's exactly what we'd do:

- **Train Gen 3+** until the agent masters Task 1 (target: 0.70+ mean reward)
- **Move to Task 2** — add battery pressure and moving obstacles
- **Scale to Task 3** — two-drone coordination and swarm strategy
- **Test generalization** on a held-out scene the agent has never seen before

The architecture works. The environment is solid. The agent is learning. We just need more training time to see it fully click.

---

## Why Any of This Matters

Drone swarms today run on pre-programmed scripts. They work well — until something unexpected happens. A drone loses battery. An obstacle moves. The mission priority changes mid-flight. Scripts can't adapt to that.

What we're building trains the gap between rigid automation and genuine adaptive intelligence. The goal is drones that can *reason*, replan in real-time, and coordinate under uncertainty.

We didn't reach the finish line in 24 hours. But we got close enough to see what's possible — and more importantly, to build the foundation to get there.

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