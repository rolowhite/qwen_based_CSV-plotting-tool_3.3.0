"""A small made-up solution library in the Walpole file layout (no book text), and the real one.

The real library (the Walpole solutions) comes with the app: plotstudio/assets/notebook. $NOTEBOOK_LIBRARY
points the tests at another file or folder instead.
"""
import os
from pathlib import Path

import pytest

SAMPLE = r"""---
book: sample
edition: 1st
chapter: 1-2
chapter_title: Placeholder chapters
exercises: 7
---
# Sample — Chapter 1: Counting

**Scope:** placeholder text for tests.

---

## Sample — Chapter 1, Section 1.1: Coins and boxes

### Exercise 1.1
**Problem:** A box holds 7 red and 5 blue marbles. Two marbles are drawn without replacement. Find the probability that both are red.

$$P=\frac{7}{12}\cdot\frac{6}{11}=\mathbf{0.3182}.$$

✔ *Checker: python gives 0.31818.*

---

### Exercise 1.2
**Problem:** For the marbles of Exercise 1.1, find the probability that the two marbles have different colours.

$$P=2\cdot\frac{7}{12}\cdot\frac{5}{11}=0.5303.$$

⚠ *Checker note: the key prints 0.53; we keep four places.*

---

### Exercise 1.3 (Lamp Test)
**Problem:** A lamp lasts an exponential time with mean 1/4 of a year. Find $P(T>0.5)$.

| $t$ | 0.25 | 0.5 |
|---|---|---|
| $P(T>t)$ | 0.3679 | 0.1353 |

$$F(t)=\begin{cases}0,&t<0\\1-e^{-4t},&t\ge0\end{cases}$$

📘 *Table check (Table A.0, placeholder): 0.1353 ✓.*

✔ *Checker: matches the key.*

---

## Sample — Chapter 1, Section 1.2: Plants

### Exercise 1.4
A plant makes 20,000 parts a day; 2% are faulty. How many faulty parts are expected each day? The answer is $0.02(20{,}000)=400$.

---

# Sample — Chapter 2: Means

## Sample — Chapter 2, Section 2.1: Sample mean

### Exercise 2.1
**Problem:** The weights of six parcels are 2.1, 3.4, 2.8, 3.0, 2.6 and 3.1 kg. Find the sample mean.

$\bar x=17/6=2.833$ kg. See also Exercise 1.1 and Exercise 9.9.

✔ *Checker: python gives 2.8333.*

---

### Exercise 2.2
**Problem:** The weights of six parcels are 4.1, 1.4, 5.8, 2.0, 6.6 and 0.1 kg. Find the sample mean.

$\bar x=20/6=3.333$ kg.

---

### Exercise 2.2
**Problem:** A duplicate heading that must be reported and dropped.
"""


def write_sample(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "Sample_Solutions.md"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def real_library() -> Path:
    from plotstudio.core.notebook.library import BUILT_IN
    path = Path(os.environ.get("NOTEBOOK_LIBRARY") or BUILT_IN).expanduser()
    if not path.exists():
        pytest.skip(f"the solutions library is missing: {path}")
    return path
