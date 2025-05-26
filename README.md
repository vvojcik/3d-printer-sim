# 3D Printer Simulator

A highly visual 3D Printer Simulator built entirely with Python, Pygame, and OpenGL. This project simulates the mechanics and step-by-step layer generation of a modern 3D printer.

## Features
* **Free-Look Camera:** Full 3D viewport manipulation.
* **Algorithmic Shape Generators:** Custom generators for printing precise 3D objects like Spheres and Cubes using geometric equations.
* **Hardware Simulation:** Articulated Gantry, Print Bed, and Nozzle movements.
* **Optimized Rendering:** Built using OpenGL Display Lists capable of holding thousands of dynamically generated blocks.

## Controls
* `C` - Print a Cube
* `V` - Print a Sphere
* `R` - Reset printer head/bed positions (Smooth Animation)
* `DELETE` - Sequentially delete printed blocks
* `Mouse Drag` - Rotate Camera
* `Mouse Wheel` - Move Gantry Forward/Backward
* `W/A/S/D` - Manual Bed & Nozzle overrides