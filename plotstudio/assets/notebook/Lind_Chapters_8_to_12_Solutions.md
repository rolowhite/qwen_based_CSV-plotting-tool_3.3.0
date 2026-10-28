---
book: lind
title: Statistical Techniques in Business and Economics
authors: Douglas A. Lind, William G. Marchal, Samuel A. Wathen
edition: 15th
chapter: 8-12
chapter_title: Chapters 8–12 Complete Solutions (Sampling, Confidence Intervals, One- & Two-Sample Hypothesis Tests, and ANOVA)
exercises: 327
---

# Lind — Chapter 8: Sampling Methods and the Central Limit Theorem

**Scope:** Every exercise in Chapter 8 of Douglas A. Lind, William G. Marchal, and Samuel A. Wathen, *Statistical Techniques in Business & Economics* (15th ed.): Section Exercises 8.1–8.4 (§8.2, pp. 272–274), 8.5–8.10 (§8.4, pp. 278–279), 8.11–8.14 (§8.5, pp. 285–286), 8.15–8.18 (§8.6, p. 289), Chapter Exercises 8.19–8.45 (pp. 290–295), and Data Set Exercises 8.46–8.48 (p. 295). Both odd-numbered and unsolved even-numbered exercises are completely worked out.

**How tables were used:** Standard normal areas follow Lind Appendix B.1 (area between $0$ and $z$, with $z$ rounded to 2 decimal places), alongside exact `scipy.stats.norm` values in the checker notes. Random-number sampling exercises use the given random numbers from the problem text and Appendix B.6 conventions.

**Conventions (Lind §§8.2–8.6):**
- Population mean $\mu = \frac{\sum X}{N}$ and population variance $\sigma^2 = \frac{\sum (X-\mu)^2}{N}$.
- Number of simple random samples without replacement of size $n$ from $N$: $_NC_n = \binom{N}{n} = \frac{N!}{n!(N-n)!}$.
- Mean of sampling distribution of sample means: $\mu_{\bar{X}} = \mu$.
- Standard error of the mean: $\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}}$, and $z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}}$.

---

## Lind — Chapter 8, Section 8.2: Sampling Methods

### Exercise 8.1
**Problem:** The following is a list of Marco's Pizza stores in Lucas County. Also noted is whether the store is corporate-owned (C) or manager-owned (M). A sample of four locations is to be selected and inspected for customer convenience, safety, cleanliness, and other features.
(a) The random numbers selected are 08, 18, 11, 54, 02, 41, and 54. Which stores are selected?
(b) Use the table of random numbers to select your own sample of locations.
(c) A sample is to consist of every seventh location. The number 03 is the starting point. Which locations will be included in the sample?
(d) Suppose a sample is to consist of three locations, of which two are corporate-owned and one is manager-owned. Select a sample accordingly.

| ID No. | Address | Type | ID No. | Address | Type |
|---|---|---|---|---|---|
| 00 | 2607 Starr Av | C | 12 | 2040 Ottawa River Rd | C |
| 01 | 309 W Alexis Rd | C | 13 | 2116 N Reynolds Rd | C |
| 02 | 2652 W Central Av | C | 14 | 3678 Rugby Dr | C |
| 03 | 630 Dixie Hwy | M | 15 | 1419 South Av | C |
| 04 | 3510 Dorr St | C | 16 | 1234 W Sylvania Av | C |
| 05 | 5055 Glendale Av | C | 17 | 4624 Woodville Rd | M |
| 06 | 3382 Lagrange St | M | 18 | 5155 S Main | M |
| 07 | 2525 W Laskey Rd | C | 19 | 106 E Airport Hwy | C |
| 08 | 303 Louisiana Av | C | 20 | 6725 W Central | M |
| 09 | 149 Main St | C | 21 | 4252 Monroe | C |
| 10 | 835 S McCord Rd | M | 22 | 2036 Woodville Rd | C |
| 11 | 3501 Monroe St | M | 23 | 1316 Michigan Av | M |

**Given:** $N = 24$ Marco's Pizza stores coded `00` to `23` (16 corporate-owned `C` and 8 manager-owned `M`).

**(a)** Valid store IDs run from `00` to `23`. Reading the random numbers `08, 18, 11, 54, 02, 41, 54` in order and skipping `54` (out of range `00`–`23`), the first four valid IDs are `08`, `18`, `11`, and `02`:
- **08:** 303 Louisiana Av (C)
- **18:** 5155 S Main (M)
- **11:** 3501 Monroe St (M)
- **02:** 2652 W Central Av (C)

**(b)** Answers will vary depending on the starting point in Appendix B.6. For example, reading two-digit numbers from Row 1 of Appendix B.6 (`02, 71, 19, 48, 73, 54, 92, 17, 76, 40, 61, 54, 51, 71, 47, 13`), the first four valid store IDs in `00`–`23` are **02 (2652 W Central Av)**, **19 (106 E Airport Hwy)**, **17 (4624 Woodville Rd)**, and **13 (2116 N Reynolds Rd)**.

**(c)** Starting at ID `03` and selecting every 7th store ($03, 03+7=10, 10+7=17$; next is $17+7=24$, which exceeds `23`):
- **03:** 630 Dixie Hwy (M)
- **10:** 835 S McCord Rd (M)
- **17:** 4624 Woodville Rd (M)

**(d)** Stratified random sample (answers will vary): Partition the 24 stores into the 16 corporate-owned stores (`00, 01, 02, 04, 05, 07, 08, 09, 12, 13, 14, 15, 16, 19, 21, 22`) and the 8 manager-owned stores (`03, 06, 10, 11, 17, 18, 20, 23`). Using random numbers (for instance from part a), select the first two corporate stores **08 (303 Louisiana Av)** and **02 (2652 W Central Av)**, and the first manager-owned store **18 (5155 S Main)**.

**Answer:** (a) Stores 08 (303 Louisiana Av), 18 (5155 S Main), 11 (3501 Monroe St), and 02 (2652 W Central Av); (b) answers vary (e.g., 02, 19, 17, 13); (c) Stores 03 (630 Dixie Hwy), 10 (835 S McCord Rd), and 17 (4624 Woodville Rd); (d) stratified sample of 2 C and 1 M (e.g., 08, 02, and 18).

✔ *Checker: Verified against Lind Appendix C (08: 303 Louisiana, 18: 5155 S. Main, 11: 3501 Monroe, 02: 2652 W. Central; systematic: 630 Dixie Hwy, 835 S. McCord Rd, 4624 Woodville Rd).*

---

### Exercise 8.2
**Problem:** The following is a list of hospitals in the Cincinnati (Ohio) and Northern Kentucky Region. Also included is whether the hospital is a general medical/surgical hospital (M/S) or a specialty hospital (S). We are interested in estimating the average number of full- and part-time nurses employed in the area hospitals.
(a) A sample of five hospitals is to be randomly selected. The random numbers are 09, 16, 00, 49, 54, 12, and 04. Which hospitals are included in the sample?
(b) Use a table of random numbers to develop your own sample of five hospitals.
(c) A sample is to consist of every fifth location. We select 02 as the starting point. Which hospitals will be included in the sample?
(d) A sample is to consist of four medical and surgical hospitals and one specialty hospital. Select an appropriate sample.

| ID Number | Name | Address | Type |
|---|---|---|---|
| 00 | Bethesda North | 10500 Montgomery, Cincinnati, Ohio 45242 | M/S |
| 01 | Ft. Hamilton-Hughes | 630 Eaton Avenue, Hamilton, Ohio 45013 | M/S |
| 02 | Jewish Hospital-Kenwood | 4700 East Galbraith Rd., Cincinnati, Ohio 45236 | M/S |
| 03 | Mercy Hospital-Fairfield | 3000 Mack Road, Fairfield, Ohio 45014 | M/S |
| 04 | Mercy Hospital-Hamilton | 100 Riverfront Plaza, Hamilton, Ohio 45011 | M/S |
| 05 | Middletown Regional | 105 McKnight Drive, Middletown, Ohio 45044 | M/S |
| 06 | Clermont Mercy Hospital | 3000 Hospital Drive, Batavia, Ohio 45103 | M/S |
| 07 | Mercy Hospital-Anderson | 7500 State Road, Cincinnati, Ohio 45255 | M/S |
| 08 | Bethesda Oak Hospital | 619 Oak Street, Cincinnati, Ohio 45206 | M/S |
| 09 | Children's Hospital Medical Center | 3333 Burnet Avenue, Cincinnati, Ohio 45229 | M/S |
| 10 | Christ Hospital | 2139 Auburn Avenue, Cincinnati, Ohio 45219 | M/S |
| 11 | Deaconess Hospital | 311 Straight Street, Cincinnati, Ohio 45219 | M/S |
| 12 | Good Samaritan Hospital | 375 Dixmyth Avenue, Cincinnati, Ohio 45220 | M/S |
| 13 | Jewish Hospital | 3200 Burnet Avenue, Cincinnati, Ohio 45229 | M/S |
| 14 | University Hospital | 234 Goodman Street, Cincinnati, Ohio 45267 | M/S |
| 15 | Providence Hospital | 2446 Kipling Avenue, Cincinnati, Ohio 45239 | M/S |
| 16 | St. Francis-St. George Hospital | 3131 Queen City Avenue, Cincinnati, Ohio 45238 | M/S |
| 17 | St. Elizabeth Medical Center, North Unit | 401 E. 20th Street, Covington, Kentucky 41014 | M/S |
| 18 | St. Elizabeth Medical Center, South Unit | One Medical Village, Edgewood, Kentucky 41017 | M/S |
| 19 | St. Luke's Hospital West | 7380 Turfway Drive, Florence, Kentucky 41075 | M/S |
| 20 | St. Luke's Hospital East | 85 North Grand Avenue, Ft. Thomas, Kentucky 41042 | M/S |
| 21 | Care Unit Hospital | 3156 Glenmore Avenue, Cincinnati, Ohio 45211 | S |
| 22 | Emerson Behavioral Science | 2446 Kipling Avenue, Cincinnati, Ohio 45239 | S |
| 23 | Pauline Warfield Lewis Center for Psychiatric Treat. | 1101 Summit Road, Cincinnati, Ohio 45237 | S |
| 24 | Children's Psychiatric No. Kentucky | 502 Farrell Drive, Covington, Kentucky 41011 | S |
| 25 | Drake Center Rehab—Long Term | 151 W. Galbraith Road, Cincinnati, Ohio 45216 | S |
| 26 | No. Kentucky Rehab Hospital—Short Term | 201 Medical Village, Edgewood, Kentucky | S |
| 27 | Shriners Burns Institute | 3229 Burnet Avenue, Cincinnati, Ohio 45229 | S |
| 28 | VA Medical Center | 3200 Vine, Cincinnati, Ohio 45220 | S |

**Given:** $N = 29$ hospitals coded `00` to `28`, where `00`–`20` (21 hospitals) are general medical/surgical (`M/S`) and `21`–`28` (8 hospitals) are specialty (`S`).

**(a)** From the random numbers `09, 16, 00, 49, 54, 12, 04`, ignore `49` and `54` because they exceed `28`. The five selected hospitals are:
- **09:** Children's Hospital Medical Center
- **16:** St. Francis-St. George Hospital
- **00:** Bethesda North
- **12:** Good Samaritan Hospital
- **04:** Mercy Hospital-Hamilton

**(b)** Using Appendix B.6 (answers will vary; e.g., reading the first two digits of the first column of Appendix B.6: `02, 94, 54, 77, 61, 17, 13, 87, 08, 78, ...` and continuing until five valid numbers in `00`–`28` are found): **02 (Jewish Hospital-Kenwood)**, **17 (St. Elizabeth Medical Center, North Unit)**, **13 (Jewish Hospital)**, **08 (Bethesda Oak Hospital)**, and **19 (St. Luke's Hospital West)**.

**(c)** Systematic sample of every 5th location starting at `02` ($02, 07, 12, 17, 22, 27$):
- **02:** Jewish Hospital-Kenwood
- **07:** Mercy Hospital-Anderson
- **12:** Good Samaritan Hospital
- **17:** St. Elizabeth Medical Center, North Unit
- **22:** Emerson Behavioral Science
- **27:** Shriners Burns Institute

**(d)** Stratified random sample of 4 `M/S` hospitals (from IDs `00`–`20`) and 1 `S` hospital (from IDs `21`–`28`): for example, selecting 4 `M/S` hospitals (**09 Children's Hospital Medical Center**, **16 St. Francis-St. George Hospital**, **00 Bethesda North**, **12 Good Samaritan Hospital**) and 1 `S` hospital (**22 Emerson Behavioral Science**).

**Answer:** (a) Hospitals 09 (Children's Hospital Medical Center), 16 (St. Francis-St. George), 00 (Bethesda North), 12 (Good Samaritan), and 04 (Mercy Hospital-Hamilton); (b) answers vary (e.g., 02, 17, 13, 08, 19); (c) Hospitals 02, 07, 12, 17, 22, and 27; (d) 4 M/S hospitals from 00–20 and 1 S hospital from 21–28 (e.g., 09, 16, 00, 12, and 22).

✔ *Checker: Verified IDs against hospital roster (`00`–`28`) and arithmetic progression $2 + 5k \le 28 \Rightarrow \{02, 07, 12, 17, 22, 27\}$.*

---

### Exercise 8.3
**Problem:** Listed below are the 35 members of the Metro Toledo Automobile Dealers Association. We would like to estimate the mean revenue from dealer service departments.
(a) We want to select a random sample of five dealers. The random numbers are: 05, 20, 59, 21, 31, 28, 49, 38, 66, 08, 29, and 02. Which dealers would be included in the sample?
(b) Use the table of random numbers to select your own sample of five dealers.
(c) A sample is to consist of every seventh dealer. The number 04 is selected as the starting point. Which dealers are included in the sample?

| ID Number | Dealer | ID Number | Dealer | ID Number | Dealer |
|---|---|---|---|---|---|
| 00 | Dave White Acura | 12 | Spurgeon Chevrolet Motor Sales, Inc. | 24 | Lexus of Toledo |
| 01 | Autofair Nissan | 13 | Dunn Chevrolet | 25 | Mathews Ford Oregon, Inc. |
| 02 | Autofair Toyota-Suzuki | 14 | Don Scott Chevrolet-Pontiac | 26 | Northtowne Chevrolet |
| 03 | George Ball's Buick GMC Truck | 15 | Dave White Chevrolet Co. | 27 | Quality Ford Sales, Inc. |
| 04 | Yark Automotive Group | 16 | Dick Wilson Pontiac | 28 | Rouen Chrysler Jeep Eagle |
| 05 | Bob Schmidt Chevrolet | 17 | Doyle Pontiac Buick | 29 | Saturn of Toledo |
| 06 | Bowling Green Lincoln Mercury Jeep Eagle | 18 | Franklin Park Lincoln Mercury | 30 | Ed Schmidt Pontiac Jeep Eagle |
| 07 | Brondes Ford | 19 | Genoa Motors | 31 | Southside Lincoln Mercury |
| 08 | Brown Honda | 20 | Great Lakes Ford Nissan | 32 | Valiton Chrysler |
| 09 | Brown Mazda | 21 | Grogan Towne Chrysler | 33 | Vin Divers |
| 10 | Charlie's Dodge | 22 | Hatfield Motor Sales | 34 | Whitman Ford |
| 11 | Thayer Chevrolet/Toyota | 23 | Kistler Ford, Inc. | | |

**Given:** $N = 35$ automobile dealers coded `00` to `34`.

**(a)** Reading the random numbers `05, 20, 59, 21, 31, 28, 49, 38, 66, 08, 29, 02` and skipping `59` (since valid IDs are `00`–`34`), the first five valid numbers are `05, 20, 21, 31, 28`:
- **05:** Bob Schmidt Chevrolet
- **20:** Great Lakes Ford Nissan
- **21:** Grogan Towne Chrysler
- **31:** Southside Lincoln Mercury
- **28:** Rouen Chrysler Jeep Eagle

**(b)** Using Appendix B.6 (answers will vary; e.g., reading Row 1 two-digit pairs `02, 71, 19, 48, 73, 54, 92, 17, 76, 40, 61, 54, 51, 71, 47, 13, 74, 88, 74, 55, 08`): **02 (Autofair Toyota-Suzuki)**, **19 (Genoa Motors)**, **17 (Doyle Pontiac Buick)**, **13 (Dunn Chevrolet)**, and **08 (Brown Honda)**.

**(c)** Starting at `04` and selecting every 7th dealer ($04, 11, 18, 25, 32$):
- **04:** Yark Automotive Group
- **11:** Thayer Chevrolet/Toyota
- **18:** Franklin Park Lincoln Mercury
- **25:** Mathews Ford Oregon, Inc.
- **32:** Valiton Chrysler

**Answer:** (a) Dealers 05 (Bob Schmidt Chevrolet), 20 (Great Lakes Ford Nissan), 21 (Grogan Towne Chrysler), 31 (Southside Lincoln Mercury), and 28 (Rouen Chrysler Jeep Eagle); (b) answers vary (e.g., 02, 19, 17, 13, 08); (c) Dealers 04 (Yark Automotive Group), 11 (Thayer Chevrolet/Toyota), 18 (Franklin Park Lincoln Mercury), 25 (Mathews Ford Oregon, Inc.), and 32 (Valiton Chrysler).

✔ *Checker: Matches Lind Appendix C exactly.*

---

### Exercise 8.4
**Problem:** Listed below are the 27 Nationwide Insurance agents in the Toledo, Ohio, metropolitan area. We would like to estimate the mean number of years employed with Nationwide.
(a) We want to select a random sample of four agents. The random numbers are: 02, 59, 51, 25, 14, 29, 77, 69, and 18. Which dealers would be included in the sample?
(b) Use the table of random numbers to select your own sample of four agents.
(c) A sample is to consist of every seventh dealer. The number 04 is selected as the starting point. Which agents will be included in the sample?

| ID Number | Agent | ID Number | Agent | ID Number | Agent |
|---|---|---|---|---|---|
| 00 | Bly Scott 3332 W Laskey Rd | 09 | Harris Ev 2026 Albon Rd | 18 | Priest Harvey 5113 N Summit St |
| 01 | Coyle Mike 5432 W Central Av | 10 | Heini Bernie 7110 W Central | 19 | Riker Craig 2621 N Reynolds Rd |
| 02 | Denker Brett 7445 Airport Hwy | 11 | Hinckley Dave 14 N Holland Sylvania Rd | 20 | Schwab Dave 572 W Dussel Dr |
| 03 | Denker Rollie 7445 Airport Hwy | 12 | Joehlin Bob 3358 Navarre Av | 21 | Seibert John H 201 S Main |
| 04 | Farley Ron 1837 W Alexis Rd | 13 | Keisser David 3030 W Sylvania Av | 22 | Smithers Bob 229 Superior St |
| 05 | George Mark 7247 W Central Av | 14 | Keisser Keith 5902 Sylvania Av | 23 | Smithers Jerry 229 Superior St |
| 06 | Gibellato Carlo 6616 Monroe St | 15 | Lawrence Grant 342 W Dussel Dr | 24 | Wright Steve 105 S Third St |
| 07 | Glemser Cathy 5602 Woodville Rd | 16 | Miller Ken 2427 Woodville Rd | 25 | Wood Tom 112 Louisiana Av |
| 08 | Green Mike 4149 Holland Sylvania Rd | 17 | O'Donnell Jim 7247 W Central Av | 26 | Yoder Scott 6 Willoughby Av |

**Given:** $N = 27$ Nationwide Insurance agents coded `00` to `26`.

**(a)** From the random numbers `02, 59, 51, 25, 14, 29, 77, 69, 18`, ignore numbers greater than `26` (`59, 51, 29, 77, 69`). The four valid IDs are `02, 25, 14, 18`:
- **02:** Denker Brett (7445 Airport Hwy)
- **25:** Wood Tom (112 Louisiana Av)
- **14:** Keisser Keith (5902 Sylvania Av)
- **18:** Priest Harvey (5113 N Summit St)

**(b)** Using Appendix B.6 (answers will vary; e.g., reading Row 1 two-digit pairs `02, 71, 19, 48, 73, 54, 92, 17, 76, 40, 61, 54, 51, 71, 47, 13`): **02 (Denker Brett)**, **19 (Riker Craig)**, **17 (O'Donnell Jim)**, and **13 (Keisser David)**.

**(c)** Starting at `04` and selecting every 7th agent ($04, 11, 18, 25$):
- **04:** Farley Ron (1837 W Alexis Rd)
- **11:** Hinckley Dave (14 N Holland Sylvania Rd)
- **18:** Priest Harvey (5113 N Summit St)
- **25:** Wood Tom (112 Louisiana Av)

**Answer:** (a) Agents 02 (Denker Brett), 25 (Wood Tom), 14 (Keisser Keith), and 18 (Priest Harvey); (b) answers vary (e.g., 02, 19, 17, 13); (c) Agents 04 (Farley Ron), 11 (Hinckley Dave), 18 (Priest Harvey), and 25 (Wood Tom).

✔ *Checker: Verified IDs in `00`–`26` and systematic indices $4 + 7k \le 26 \Rightarrow \{04, 11, 18, 25\}$.*

---

## Lind — Chapter 8, Section 8.4: Sampling Distribution of the Sample Mean

### Exercise 8.5
**Problem:** A population consists of the following four values: 12, 12, 14, and 16.
(a) List all samples of size 2, and compute the mean of each sample.
(b) Compute the mean of the distribution of the sample mean and the population mean. Compare the two values.
(c) Compare the dispersion in the population with that of the sample mean.

**Given:** Population values $X \in \{12, 12, 14, 16\}$ ($N = 4$), sample size $n = 2$ without replacement.

**(a)** There are $\binom{4}{2} = 6$ possible samples of size $n = 2$:

| Sample | Values | Sum | Mean ($\bar{X}$) |
|---|---|---|---|
| 1 | 12, 12 | 24 | 12.0 |
| 2 | 12, 14 | 26 | 13.0 |
| 3 | 12, 16 | 28 | 14.0 |
| 4 | 12, 14 | 26 | 13.0 |
| 5 | 12, 16 | 28 | 14.0 |
| 6 | 14, 16 | 30 | 15.0 |

**(b)** Population mean and mean of the sample means:
$$\mu = \frac{12 + 12 + 14 + 16}{4} = \frac{54}{4} = \mathbf{13.5}, \qquad \mu_{\bar{X}} = \frac{12 + 13 + 14 + 13 + 14 + 15}{6} = \frac{81}{6} = \mathbf{13.5}.$$
The two means are **identical** ($\mu_{\bar{X}} = \mu = 13.5$).

**(c)** The population values range from $12$ to $16$ (range $= 4$, population standard deviation $\sigma = \sqrt{2.75} \approx 1.6583$), whereas the sample means range only from $12.0$ to $15.0$ (range $= 3$, standard deviation $\sigma_{\bar{X}} = \sqrt{0.9167} \approx 0.9574$). Thus, **there is less dispersion in the distribution of the sample mean than in the population**.

**Answer:** (a) Sample means: 12, 13, 14, 13, 14, 15; (b) $\mu_{\bar{X}} = 13.5$ and $\mu = 13.5$ (identical); (c) the sample means have less dispersion (range 12 to 15) than the population (range 12 to 16).

✔ *Checker: Matches Lind Appendix C ($\mu = 13.5$, $\mu_{\bar{X}} = 13.5$, sample means vary from 12 to 15 vs. population 12 to 16).*

---

### Exercise 8.6
**Problem:** A population consists of the following five values: 2, 2, 4, 4, and 8.
(a) List all samples of size 2, and compute the mean of each sample.
(b) Compute the mean of the distribution of sample means and the population mean. Compare the two values.
(c) Compare the dispersion in the population with that of the sample means.

**Given:** Population values $X \in \{2, 2, 4, 4, 8\}$ ($N = 5$), sample size $n = 2$ without replacement.

**(a)** There are $\binom{5}{2} = 10$ possible samples of size $n = 2$:

| Sample | Values | Sum | Mean ($\bar{X}$) |
|---|---|---|---|
| 1 | 2, 2 | 4 | 2.0 |
| 2 | 2, 4 | 6 | 3.0 |
| 3 | 2, 4 | 6 | 3.0 |
| 4 | 2, 8 | 10 | 5.0 |
| 5 | 2, 4 | 6 | 3.0 |
| 6 | 2, 4 | 6 | 3.0 |
| 7 | 2, 8 | 10 | 5.0 |
| 8 | 4, 4 | 8 | 4.0 |
| 9 | 4, 8 | 12 | 6.0 |
| 10 | 4, 8 | 12 | 6.0 |

**(b)** Population mean and mean of the sample means:
$$\mu = \frac{2 + 2 + 4 + 4 + 8}{5} = \frac{20}{5} = \mathbf{4.0}, \qquad \mu_{\bar{X}} = \frac{2 + 3 + 3 + 5 + 3 + 3 + 5 + 4 + 6 + 6}{10} = \frac{40}{10} = \mathbf{4.0}.$$
The two means are **identical** ($\mu_{\bar{X}} = \mu = 4.0$).

**(c)** The population values range from $2$ to $8$ (range $= 6$, population standard deviation $\sigma = \sqrt{4.8} \approx 2.1909$), whereas the sample means range from $2.0$ to $6.0$ (range $= 4$, $\sigma_{\bar{X}} = \sqrt{1.8} \approx 1.3416$). **The dispersion in the population is greater than the dispersion in the distribution of sample means.**

**Answer:** (a) Sample means: 2, 3, 3, 5, 3, 3, 5, 4, 6, 6; (b) $\mu_{\bar{X}} = 4.0$ and $\mu = 4.0$ (equal); (c) the sample means have less dispersion (range 2 to 6) than the population (range 2 to 8).

✔ *Checker: Recomputed in Python; $\mu = 4.0$, $\mu_{\bar{X}} = 4.0$, $\sigma^2 = 4.8$, $\sigma_{\bar{X}}^2 = 1.8$.*

---

### Exercise 8.7
**Problem:** A population consists of the following five values: 12, 12, 14, 15, and 20.
(a) List all samples of size 3, and compute the mean of each sample.
(b) Compute the mean of the distribution of sample means and the population mean. Compare the two values.
(c) Compare the dispersion in the population with that of the sample means.

**Given:** Population values $X \in \{12, 12, 14, 15, 20\}$ ($N = 5$), sample size $n = 3$ without replacement.

**(a)** There are $\binom{5}{3} = 10$ possible samples of size $n = 3$:

| Sample | Values | Sum | Mean ($\bar{X}$) |
|---|---|---|---|
| 1 | 12, 12, 14 | 38 | 12.67 |
| 2 | 12, 12, 15 | 39 | 13.00 |
| 3 | 12, 12, 20 | 44 | 14.67 |
| 4 | 12, 14, 15 | 41 | 13.67 |
| 5 | 12, 14, 20 | 46 | 15.33 |
| 6 | 12, 15, 20 | 47 | 15.67 |
| 7 | 12, 14, 15 | 41 | 13.67 |
| 8 | 12, 14, 20 | 46 | 15.33 |
| 9 | 12, 15, 20 | 47 | 15.67 |
| 10 | 14, 15, 20 | 49 | 16.33 |

**(b)** Population mean and mean of the sample means:
$$\mu = \frac{12 + 12 + 14 + 15 + 20}{5} = \frac{73}{5} = \mathbf{14.6}, \qquad \mu_{\bar{X}} = \frac{438/3}{10} = \frac{146}{10} = \mathbf{14.6}.$$
The two values are **identical** ($\mu_{\bar{X}} = \mu = 14.6$).

**(c)** The population values vary from $12$ to $20$ (range $= 8$, $\sigma = \sqrt{8.64} \approx 2.9394$), whereas the sample means vary from $12.67$ to $16.33$ (range $= 3.67$, $\sigma_{\bar{X}} = \sqrt{1.44} = 1.20$). **The dispersion of the population is greater than that of the sample means.**

**Answer:** (a) Sample means: 12.67, 13.00, 14.67, 13.67, 15.33, 15.67, 13.67, 15.33, 15.67, 16.33; (b) $\mu_{\bar{X}} = 14.6$ and $\mu = 14.6$ (equal); (c) the population has greater dispersion (12 to 20) than the sample means (12.67 to 16.33).

✔ *Checker: Matches Lind Appendix C ($\mu = 14.6$, $\mu_{\bar{X}} = 14.6$, range 12.67 to 16.33 vs. 12 to 20).*

---

### Exercise 8.8
**Problem:** A population consists of the following five values: 0, 0, 1, 3, 6.
(a) List all samples of size 3, and compute the mean of each sample.
(b) Compute the mean of the distribution of sample means and the population mean. Compare the two values.
(c) Compare the dispersion in the population with that of the sample means.

**Given:** Population values $X \in \{0, 0, 1, 3, 6\}$ ($N = 5$), sample size $n = 3$ without replacement.

**(a)** There are $\binom{5}{3} = 10$ possible samples of size $n = 3$:

| Sample | Values | Sum | Mean ($\bar{X}$) |
|---|---|---|---|
| 1 | 0, 0, 1 | 1 | 0.33 |
| 2 | 0, 0, 3 | 3 | 1.00 |
| 3 | 0, 0, 6 | 6 | 2.00 |
| 4 | 0, 1, 3 | 4 | 1.33 |
| 5 | 0, 1, 6 | 7 | 2.33 |
| 6 | 0, 3, 6 | 9 | 3.00 |
| 7 | 0, 1, 3 | 4 | 1.33 |
| 8 | 0, 1, 6 | 7 | 2.33 |
| 9 | 0, 3, 6 | 9 | 3.00 |
| 10 | 1, 3, 6 | 10 | 3.33 |

**(b)** Population mean and mean of the sample means:
$$\mu = \frac{0 + 0 + 1 + 3 + 6}{5} = \frac{10}{5} = \mathbf{2.0}, \qquad \mu_{\bar{X}} = \frac{60/3}{10} = \frac{20}{10} = \mathbf{2.0}.$$
They are **identical** ($\mu_{\bar{X}} = \mu = 2.0$).

**(c)** The population values vary from $0$ to $6$ (range $= 6$, $\sigma = \sqrt{5.2} \approx 2.2804$), while the sample means vary from $0.33$ to $3.33$ (range $= 3.0$, $\sigma_{\bar{X}} = \sqrt{5.2/6} \approx 0.9309$). **The population has greater dispersion than the distribution of sample means.**

**Answer:** (a) Sample means: 0.33, 1.00, 2.00, 1.33, 2.33, 3.00, 1.33, 2.33, 3.00, 3.33; (b) $\mu_{\bar{X}} = 2.0$ and $\mu = 2.0$ (equal); (c) the sample means have less dispersion (0.33 to 3.33) than the population (0 to 6).

✔ *Checker: Recomputed in Python; $\mu = 2.0$, $\mu_{\bar{X}} = 2.0$.*

---

### Exercise 8.9
**Problem:** In the law firm Tybo and Associates, there are six partners. Listed next is the number of cases each associate actually tried in court last month.
(a) How many different samples of 3 are possible?
(b) List all possible samples of size 3, and compute the mean number of cases in each sample.
(c) Compare the mean of the distribution of sample means to the population mean.
(d) On a chart similar to Chart 8–1, compare the dispersion in the population with that of the sample means.

| Associate | Number of Cases |
|---|---|
| Ruud | 3 |
| Wu | 6 |
| Sass | 3 |
| Flores | 3 |
| Wilhelms | 0 |
| Schueller | 1 |

**Given:** $N = 6$ partners with cases $\{3, 6, 3, 3, 0, 1\}$, sample size $n = 3$ without replacement.

**(a)** Number of possible samples of size 3:
$$_6C_3 = \frac{6!}{3!(6-3)!} = \frac{6 \times 5 \times 4}{3 \times 2 \times 1} = \mathbf{20}.$$

**(b)** All 20 possible samples of size 3 and their means:

| # | Partners | Cases | Sum | Mean ($\bar{X}$) | # | Partners | Cases | Sum | Mean ($\bar{X}$) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Ruud, Wu, Sass | 3, 6, 3 | 12 | 4.00 | 11 | Wu, Sass, Flores | 6, 3, 3 | 12 | 4.00 |
| 2 | Ruud, Wu, Flores | 3, 6, 3 | 12 | 4.00 | 12 | Wu, Sass, Wilhelms | 6, 3, 0 | 9 | 3.00 |
| 3 | Ruud, Wu, Wilhelms | 3, 6, 0 | 9 | 3.00 | 13 | Wu, Sass, Schueller | 6, 3, 1 | 10 | 3.33 |
| 4 | Ruud, Wu, Schueller | 3, 6, 1 | 10 | 3.33 | 14 | Wu, Flores, Wilhelms | 6, 3, 0 | 9 | 3.00 |
| 5 | Ruud, Sass, Flores | 3, 3, 3 | 9 | 3.00 | 15 | Wu, Flores, Schueller | 6, 3, 1 | 10 | 3.33 |
| 6 | Ruud, Sass, Wilhelms | 3, 3, 0 | 6 | 2.00 | 16 | Wu, Wilhelms, Schueller | 6, 0, 1 | 7 | 2.33 |
| 7 | Ruud, Sass, Schueller | 3, 3, 1 | 7 | 2.33 | 17 | Sass, Flores, Wilhelms | 3, 3, 0 | 6 | 2.00 |
| 8 | Ruud, Flores, Wilhelms | 3, 3, 0 | 6 | 2.00 | 18 | Sass, Flores, Schueller | 3, 3, 1 | 7 | 2.33 |
| 9 | Ruud, Flores, Schueller | 3, 3, 1 | 7 | 2.33 | 19 | Sass, Wilhelms, Schueller | 3, 0, 1 | 4 | 1.33 |
| 10 | Ruud, Wilhelms, Schueller | 3, 0, 1 | 4 | 1.33 | 20 | Flores, Wilhelms, Schueller | 3, 0, 1 | 4 | 1.33 |

Sampling distribution of $\bar{X}$:

| Sample Mean ($\bar{X}$) | Frequency | Probability |
|---|---|---|
| 1.33 | 3 | 0.15 |
| 2.00 | 3 | 0.15 |
| 2.33 | 4 | 0.20 |
| 3.00 | 4 | 0.20 |
| 3.33 | 3 | 0.15 |
| 4.00 | 3 | 0.15 |
| **Total** | **20** | **1.00** |

**(c)** Population mean and mean of the sample means:
$$\mu = \frac{3 + 6 + 3 + 3 + 0 + 1}{6} = \frac{16}{6} = \mathbf{2.67}, \qquad \mu_{\bar{X}} = \frac{160/3}{20} = \frac{53.33}{20} = \mathbf{2.67}.$$
They are **equal**.

**(d)** Comparison of distributions:
```
Population (N=6, range 0 to 6):
0: *        (p=1/6)
1: *        (p=1/6)
3: ***      (p=3/6)
6: *        (p=1/6)

Sample Means (n=3, 20 samples, range 1.33 to 4.00, symmetric & mound-shaped):
1.33: ***   (p=0.15)
2.00: ***   (p=0.15)
2.33: ****  (p=0.20)
3.00: ****  (p=0.20)
3.33: ***   (p=0.15)
4.00: ***   (p=0.15)
```
The population has more dispersion (varying from $0$ to $6$, range $= 6$) than the sample means (varying from $1.33$ to $4.00$, range $= 2.67$), and the distribution of sample means is symmetric and bell-shaped.

**Answer:** (a) 20 samples; (b) means are 1.33 (3 times), 2.00 (3 times), 2.33 (4 times), 3.00 (4 times), 3.33 (3 times), 4.00 (3 times); (c) $\mu = 2.67$ and $\mu_{\bar{X}} = 2.67$ (equal); (d) the population has greater dispersion (0 to 6) than the sample means (1.33 to 4.00).

✔ *Checker: Matches Lind Appendix C ($20$, $\mu = \mu_{\bar{X}} = 2.67$, sample means range $1.33$ to $4.00$ vs. population $0$ to $6$).*

---

### Exercise 8.10
**Problem:** There are five sales associates at Mid-Motors Ford. The five representatives and the number of cars they sold last week are:
(a) How many different samples of size 2 are possible?
(b) List all possible samples of size 2, and compute the mean of each sample.
(c) Compare the mean of the sampling distribution of sample means with that of the population.
(d) On a chart similar to Chart 8–1, compare the dispersion in sample means with that of the population.

| Sales Representative | Cars Sold |
|---|---|
| Peter Hankish | 8 |
| Connie Stallter | 6 |
| Juan Lopez | 4 |
| Ted Barnes | 10 |
| Peggy Chu | 6 |

**Given:** $N = 5$ sales associates with cars sold $\{8, 6, 4, 10, 6\}$, sample size $n = 2$ without replacement.

**(a)** Number of possible samples of size 2:
$$_5C_2 = \frac{5!}{2!(5-2)!} = \frac{5 \times 4}{2} = \mathbf{10}.$$

**(b)** All 10 possible samples of size 2 and their means:

| # | Representatives | Cars Sold | Sum | Mean ($\bar{X}$) |
|---|---|---|---|---|
| 1 | Hankish, Stallter | 8, 6 | 14 | 7.0 |
| 2 | Hankish, Lopez | 8, 4 | 12 | 6.0 |
| 3 | Hankish, Barnes | 8, 10 | 18 | 9.0 |
| 4 | Hankish, Chu | 8, 6 | 14 | 7.0 |
| 5 | Stallter, Lopez | 6, 4 | 10 | 5.0 |
| 6 | Stallter, Barnes | 6, 10 | 16 | 8.0 |
| 7 | Stallter, Chu | 6, 6 | 12 | 6.0 |
| 8 | Lopez, Barnes | 4, 10 | 14 | 7.0 |
| 9 | Lopez, Chu | 4, 6 | 10 | 5.0 |
| 10 | Barnes, Chu | 10, 6 | 16 | 8.0 |

Sampling distribution of $\bar{X}$:

| Sample Mean ($\bar{X}$) | Frequency | Probability |
|---|---|---|
| 5.0 | 2 | 0.20 |
| 6.0 | 2 | 0.20 |
| 7.0 | 3 | 0.30 |
| 8.0 | 2 | 0.20 |
| 9.0 | 1 | 0.10 |
| **Total** | **10** | **1.00** |

**(c)** Population mean and mean of the sample means:
$$\mu = \frac{8 + 6 + 4 + 10 + 6}{5} = \frac{34}{5} = \mathbf{6.8}, \qquad \mu_{\bar{X}} = \frac{7 + 6 + 9 + 7 + 5 + 8 + 6 + 7 + 5 + 8}{10} = \frac{68}{10} = \mathbf{6.8}.$$
They are **identical** ($\mu_{\bar{X}} = \mu = 6.8$).

**(d)** The population ranges from $4$ to $10$ (range $= 6$, $\sigma = \sqrt{4.16} \approx 2.0396$), whereas the sample means range from $5.0$ to $9.0$ (range $= 4$, $\sigma_{\bar{X}} = \sqrt{1.56} \approx 1.2490$). **The sample means have less dispersion than the population.**

**Answer:** (a) 10 samples; (b) sample means: 5.0 (twice), 6.0 (twice), 7.0 (3 times), 8.0 (twice), 9.0 (once); (c) $\mu_{\bar{X}} = 6.8$ and $\mu = 6.8$ (equal); (d) the sample means have less dispersion (5 to 9) than the population (4 to 10).

✔ *Checker: Recomputed in Python; $\binom{5}{2} = 10$, $\mu = \mu_{\bar{X}} = 6.8$.*

---

## Lind — Chapter 8, Section 8.5: The Central Limit Theorem

### Exercise 8.11
**Problem:** Appendix B.6 is a table of random numbers. Hence, each digit from 0 to 9 has the same likelihood of occurrence.
(a) Draw a graph showing the population distribution. What is the population mean?
(b) Following are the first 10 rows of five digits from Appendix B.6. Assume that these are 10 random samples of five values each. Determine the mean of each sample and plot the means on a chart similar to Chart 8–3. Compare the mean of the sampling distribution of the sample means with the population mean.
0 2 7 1 1 / 9 4 8 7 3 / 5 4 9 2 1 / 7 7 6 4 0 / 6 1 5 4 5 / 1 7 1 4 7 / 1 3 7 4 8 / 8 7 4 5 5 / 0 8 9 9 9 / 7 8 8 0 4

**Given:** Discrete uniform population on digits $\{0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}$ with $P(X = x) = 0.10$ for each digit; 10 samples of size $n = 5$.

**(a)** The population distribution is uniform (flat) over $0, 1, \dots, 9$ with probability $0.10$ at each integer. The population mean is:
$$\mu = \frac{0 + 1 + 2 + 3 + 4 + 5 + 6 + 7 + 8 + 9}{10} = \frac{45}{10} = \mathbf{4.5}.$$

**(b)** Computing the sum and sample mean $\bar{X}$ for each of the 10 rows of $n = 5$ digits:

| Sample | Digits | Sum | Sample Mean ($\bar{X}$) |
|---|---|---|---|
| 1 | 0, 2, 7, 1, 1 | 11 | 2.2 |
| 2 | 9, 4, 8, 7, 3 | 31 | 6.2 |
| 3 | 5, 4, 9, 2, 1 | 21 | 4.2 |
| 4 | 7, 7, 6, 4, 0 | 24 | 4.8 |
| 5 | 6, 1, 5, 4, 5 | 21 | 4.2 |
| 6 | 1, 7, 1, 4, 7 | 20 | 4.0 |
| 7 | 1, 3, 7, 4, 8 | 23 | 4.6 |
| 8 | 8, 7, 4, 5, 5 | 29 | 5.8 |
| 9 | 0, 8, 9, 9, 9 | 35 | 7.0 |
| 10 | 7, 8, 8, 0, 4 | 27 | 5.4 |

Mean of the 10 sample means:
$$\bar{\bar{X}} = \frac{2.2 + 6.2 + 4.2 + 4.8 + 4.2 + 4.0 + 4.6 + 5.8 + 7.0 + 5.4}{10} = \frac{48.4}{10} = \mathbf{4.84}.$$
The mean of the 10 sample means ($4.84$) is close to the population mean ($4.50$). Moreover, the sample means range from $2.2$ to $7.0$ and cluster between $4.0$ and $5.8$, whereas the population values range from $0$ to $9$.

**Answer:** (a) Uniform distribution on $0, 1, \dots, 9$ with $\mu = 4.5$; (b) sample means are 2.2, 6.2, 4.2, 4.8, 4.2, 4.0, 4.6, 5.8, 7.0, and 5.4, with overall mean $\bar{\bar{X}} = 4.84$ (close to $\mu = 4.5$).

✔ *Checker: Matches Lind Appendix C ($\mu = 4.5$, sample means sum to $48.4$, mean $= 4.84$).*

---

### Exercise 8.12
**Problem:** Scrapper Elevator Company has 20 sales representatives who sell its product throughout the United States and Canada. The number of units sold last month by each representative is listed below. Assume these sales figures to be the population values.
2 3 2 3 3 4 2 4 3 2 2 7 3 4 5 3 3 3 3 5
(a) Draw a graph showing the population distribution.
(b) Compute the mean of the population.
(c) Select five random samples of 5 each. Compute the mean of each sample. Use the methods described in this chapter and Appendix B.6 to determine the items to be included in the sample.
(d) Compare the mean of the sampling distribution of the sample means to the population mean. Would you expect the two values to be about the same?
(e) Draw a histogram of the sample means. Do you notice a difference in the shape of the distribution of sample means compared to the shape of the population distribution?

**Given:** Population of $N = 20$ sales figures: $2, 3, 2, 3, 3, 4, 2, 4, 3, 2, 2, 7, 3, 4, 5, 3, 3, 3, 3, 5$.

**(a)** Population frequency distribution (positively skewed due to the tail at 5 and 7):

| Units Sold ($X$) | Frequency | Relative Frequency |
|---|---|---|
| 2 | 5 | 0.25 |
| 3 | 9 | 0.45 |
| 4 | 3 | 0.15 |
| 5 | 2 | 0.10 |
| 6 | 0 | 0.00 |
| 7 | 1 | 0.05 |
| **Total** | **20** | **1.00** |

**(b)** Population mean:
$$\mu = \frac{\sum X}{N} = \frac{5(2) + 9(3) + 3(4) + 2(5) + 1(7)}{20} = \frac{66}{20} = \mathbf{3.30\text{ units}}.$$
(Population standard deviation $\sigma = \sqrt{1.51} \approx 1.2288$.)

**(c)** Indexing the 20 representatives from `00` to `19` and selecting 5 random samples of size $n = 5$ using Appendix B.6 (answers will vary; illustrative random samples shown below):
- **Sample 1** (IDs 02, 19, 17, 13, 08 $\to$ values $2, 5, 3, 4, 3$): $\bar{X}_1 = \frac{17}{5} = 3.40$
- **Sample 2** (IDs 00, 04, 11, 15, 06 $\to$ values $2, 3, 7, 3, 2$): $\bar{X}_2 = \frac{17}{5} = 3.40$
- **Sample 3** (IDs 01, 05, 09, 12, 14 $\to$ values $3, 4, 2, 3, 5$): $\bar{X}_3 = \frac{17}{5} = 3.40$
- **Sample 4** (IDs 03, 07, 10, 16, 18 $\to$ values $3, 4, 2, 3, 3$): $\bar{X}_4 = \frac{15}{5} = 3.00$
- **Sample 5** (IDs 01, 03, 05, 13, 17 $\to$ values $3, 3, 4, 4, 3$): $\bar{X}_5 = \frac{17}{5} = 3.40$

**(d)** The mean of the five sample means is $\bar{\bar{X}} = \frac{3.40 + 3.40 + 3.40 + 3.00 + 3.40}{5} = \mathbf{3.32}$, which is very close to the population mean $\mu = 3.30$. Yes, by the Central Limit Theorem and unbiasedness of $\bar{X}$, the average of random sample means is expected to be close to $\mu = 3.30$.

**(e)** Compared to the population distribution (which is positively skewed and spans from $2$ to $7$), the histogram of sample means is **much narrower (concentrated around $3.0$–$3.6$) and more bell-shaped/symmetric**.

**Answer:** (a) Positively skewed distribution peaking at 3 ($f=9$); (b) $\mu = 3.30$; (c)–(d) sample means average close to $\mu = 3.30$ (e.g., $\bar{\bar{X}} = 3.32$); (e) the sample means have less dispersion and a more bell-shaped distribution than the skewed population.

✔ *Checker: Verified sum $\sum X = 66$, $N = 20$, $\mu = 3.30$.*

---

### Exercise 8.13
**Problem:** Consider all of the coins (pennies, nickels, quarters, etc.) in your pocket or purse as a population. Make a frequency table beginning with the current year and counting backward to record the ages (in years) of the coins. For example, if the current year is 2009, then a coin with 2007 stamped on it is 2 years old.
(a) Draw a histogram or other graph showing the population distribution.
(b) Randomly select five coins and record the mean age of the sampled coins. Repeat this sampling process 20 times. Now draw a histogram or other graph showing the distribution of the sample means.
(c) Compare the shapes of the two histograms.

**Given:** Empirical classroom/student coin-sampling exercise ($n = 5$, 20 repeated samples).

**(a)** Answers will vary depending on the coins in your possession. Typically, the population distribution of coin ages is **strongly right-skewed (positively skewed)**, with many recent coins ($0$–$5$ years old) and a long right tail extending to $20+$ years.

**(b)** Selecting 20 random samples of $n = 5$ coins and computing each sample mean $\bar{X}$ produces values clustered near the population mean age $\mu$, with a much narrower range than individual coins.

**(c)** While the population histogram of individual coin ages is strongly positively skewed, the histogram of the 20 sample means ($n = 5$) is **much more symmetric, mound-shaped (approaching a normal distribution by the Central Limit Theorem), and has significantly less dispersion** ($\sigma_{\bar{X}} = \sigma / \sqrt{5}$).

**Answer:** (a)–(b) Answers vary by coin collection; (c) the population distribution of coin ages is positively skewed, whereas the distribution of sample means ($n=5$) has much less dispersion and is more mound-shaped/normal by the Central Limit Theorem.

✔ *Checker: Matches Lind Appendix C ("Answers will vary depending on the coins in your possession").*

---

### Exercise 8.14
**Problem:** Consider the digits in the phone numbers on a randomly selected page of your local phone book a population. Make a frequency table of the final digit of 30 randomly selected phone numbers. For example, if a phone number is 555-9704, record a 4.
(a) Draw a histogram or other graph of this population distribution. Using the uniform distribution, compute the population mean and the population standard deviation.
(b) Also record the sample mean of the final four digits (9704 would lead to a mean of 5). Now draw a histogram or other graph showing the distribution of the sample means.
(c) Compare the shapes of the two histograms.

**Given:** Final digits $X \in \{0, 1, 2, 3, 4, 5, 6, 7, 8, 9\}$ modeled as a uniform distribution; sample means of the final $n = 4$ digits of 30 phone numbers.

**(a)** Under the discrete uniform distribution on $\{0, 1, \dots, 9\}$ (10 equally likely values with probability $0.10$ each):
$$\mu = \frac{0 + 9}{2} = \mathbf{4.50}, \qquad \sigma = \sqrt{\frac{\sum_{x=0}^9 (x - 4.5)^2}{10}} = \sqrt{\frac{82.5}{10}} = \sqrt{8.25} \approx \mathbf{2.8723}.$$
(Note: Using the continuous uniform approximation formula from Chapter 7 with $a = 0, b = 9$, $\sigma = \frac{9-0}{\sqrt{12}} = \mathbf{2.5981}$.) The population histogram is approximately **flat (uniform)** across $0$ to $9$.

**(b)** Recording the mean of the last $n = 4$ digits for 30 phone numbers yields sample means centered near $\mu = 4.50$, with theoretical standard error $\sigma_{\bar{X}} = \sigma / \sqrt{4} = 2.8723 / 2 = \mathbf{1.4361}$ (or $2.5981 / 2 = 1.2990$).

**(c)** The population histogram of single final digits is **flat/uniform** across $0$ to $9$, whereas the histogram of the 4-digit sample means is **mound-shaped (bell-shaped) and centered around 4.5 with roughly half the spread** of the individual digits, illustrating the Central Limit Theorem.

**Answer:** (a) Uniform distribution with $\mu = 4.50$ and $\sigma = \sqrt{8.25} \approx 2.872$ (or $(9-0)/\sqrt{12} \approx 2.598$); (b)–(c) the single-digit distribution is flat/uniform from 0 to 9, whereas the distribution of 4-digit sample means is bell-shaped and narrower around 4.5.

✔ *Checker: Verified $\mu = 4.50$, discrete uniform $\sigma = \sqrt{8.25} = 2.87228$, continuous uniform formula $\sigma = 9/\sqrt{12} = 2.59808$.*

---

## Lind — Chapter 8, Section 8.6: Using the Sampling Distribution of the Sample Mean

### Exercise 8.15
**Problem:** A normal population has a mean of 60 and a standard deviation of 12. You select a random sample of 9. Compute the probability the sample mean is:
(a) Greater than 63.
(b) Less than 56.
(c) Between 56 and 63.

**Given:** Normal population with $\mu = 60$, $\sigma = 12$, sample size $n = 9$.

Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{12}{\sqrt{9}} = \frac{12}{3} = 4.0.$$

**(a)** For $\bar{X} = 63$:
$$z = \frac{63 - 60}{4} = \mathbf{0.75}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.75$ is $0.2734$, so:
$$P(\bar{X} > 63) = 0.5000 - 0.2734 = \mathbf{0.2266}.$$

**(b)** For $\bar{X} = 56$:
$$z = \frac{56 - 60}{4} = \mathbf{-1.00}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.00$ is $0.3413$, so:
$$P(\bar{X} < 56) = 0.5000 - 0.3413 = \mathbf{0.1587}.$$

**(c)** Between $56$ and $63$ ($z = -1.00$ to $z = 0.75$):
$$P(56 < \bar{X} < 63) = 0.3413 + 0.2734 = \mathbf{0.6147}.$$

**Answer:** (a) $0.2266$; (b) $0.1587$; (c) $0.6147$.

✔ *Checker: Matches Lind Appendix C ($0.2266$, $0.1587$, $0.6147$).*

---

### Exercise 8.16
**Problem:** A normal population has a mean of 75 and a standard deviation of 5. You select a sample of 40. Compute the probability the sample mean is:
(a) Less than 74.
(b) Between 74 and 76.
(c) Between 76 and 77.
(d) Greater than 77.

**Given:** Normal population with $\mu = 75$, $\sigma = 5$, sample size $n = 40$.

Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{5}{\sqrt{40}} \approx 0.79057.$$

**(a)** For $\bar{X} = 74$:
$$z = \frac{74 - 75}{5 / \sqrt{40}} = \frac{-1}{0.79057} = \mathbf{-1.26}\text{ (exact }-1.2649\text{)}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.26$ is $0.3962$, so:
$$P(\bar{X} < 74) = 0.5000 - 0.3962 = \mathbf{0.1038}\text{ (exact }0.10295\text{)}.$$

**(b)** For $\bar{X} = 76$, $z = +1.26$ (area $0.3962$):
$$P(74 < \bar{X} < 76) = 0.3962 + 0.3962 = \mathbf{0.7924}\text{ (exact }0.79410\text{)}.$$

**(c)** For $\bar{X} = 77$:
$$z = \frac{77 - 75}{5 / \sqrt{40}} = \frac{2}{0.79057} = \mathbf{2.53}.$$
📘 From Appendix B.1, the area for $z = 2.53$ is $0.4943$ and for $z = 1.26$ is $0.3962$, so:
$$P(76 < \bar{X} < 77) = 0.4943 - 0.3962 = \mathbf{0.0981}\text{ (exact }0.09726\text{)}.$$

**(d)** For $\bar{X} > 77$ ($z > 2.53$):
$$P(\bar{X} > 77) = 0.5000 - 0.4943 = \mathbf{0.0057}\text{ (exact }0.00570\text{)}.$$

**Answer:** (a) $0.1038$; (b) $0.7924$; (c) $0.0981$; (d) $0.0057$.

✔ *Checker: Python recomputation gives $z = \pm 1.2649, 2.5298$; table probabilities $0.1038, 0.7924, 0.0981, 0.0057$ sum to $1.0000$.*

---

### Exercise 8.17
**Problem:** The rent for a one-bedroom apartment in Southern California follows the normal distribution with a mean of $2,200 per month and a standard deviation of $250 per month. The distribution of the monthly costs does not follow the normal distribution. In fact, it is positively skewed. What is the probability of selecting a sample of 50 one-bedroom apartments and finding the mean to be at least $1,950 per month?

**Given:** $\mu = \$2,200$, $\sigma = \$250$, $n = 50$ (positively skewed population, but $n = 50 \ge 30$ so the Central Limit Theorem applies).

Compute the standard error and $z$-value for $\bar{X} = \$1,950$:
$$\sigma_{\bar{X}} = \frac{250}{\sqrt{50}} \approx 35.3553, \qquad z = \frac{1,950 - 2,200}{250 / \sqrt{50}} = \frac{-250}{35.3553} = \mathbf{-7.07}.$$
Because $z = -7.07$ is more than $7$ standard errors below the mean, the area to the right of $z = -7.07$ is:
$$P(\bar{X} \ge 1,950) = P(Z \ge -7.07) \approx \mathbf{1.0000}\text{ (virtually certain)}.$$

**Answer:** $z = -7.07$, so $P(\bar{X} \ge \$1,950) \approx \mathbf{1.0000}$ (virtually certain).

✔ *Checker: Matches Lind Appendix C ($z = -7.07$, $P = 1$, or virtually certain).*

---

### Exercise 8.18
**Problem:** According to an IRS study, it takes a mean of 330 minutes for taxpayers to prepare, copy, and electronically file a 1040 tax form. This distribution of times follows the normal distribution and the standard deviation is 80 minutes. A consumer watchdog agency selects a random sample of 40 taxpayers.
(a) What is the standard error of the mean in this example?
(b) What is the likelihood the sample mean is greater than 320 minutes?
(c) What is the likelihood the sample mean is between 320 and 350 minutes?
(d) What is the likelihood the sample mean is greater than 350 minutes?

**Given:** Normal distribution with $\mu = 330$ minutes, $\sigma = 80$ minutes, $n = 40$.

**(a)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{80}{\sqrt{40}} \approx \mathbf{12.6491\text{ minutes}}\text{ (or }12.65\text{ minutes)}.$$

**(b)** For $\bar{X} = 320$:
$$z = \frac{320 - 330}{80 / \sqrt{40}} = \frac{-10}{12.6491} = \mathbf{-0.79}.$$
📘 From Appendix B.1, the area between $0$ and $z = -0.79$ is $0.2852$, so:
$$P(\bar{X} > 320) = 0.5000 + 0.2852 = \mathbf{0.7852}\text{ (exact }0.78540\text{)}.$$

**(c)** For $\bar{X} = 350$:
$$z = \frac{350 - 330}{80 / \sqrt{40}} = \frac{20}{12.6491} = \mathbf{1.58}.$$
📘 From Appendix B.1, the area between $0$ and $z = 1.58$ is $0.4429$, so:
$$P(320 < \bar{X} < 350) = 0.2852 + 0.4429 = \mathbf{0.7281}\text{ (exact }0.72855\text{)}.$$

**(d)** For $\bar{X} > 350$ ($z > 1.58$):
$$P(\bar{X} > 350) = 0.5000 - 0.4429 = \mathbf{0.0571}\text{ (exact }0.05692\text{)}.$$

**Answer:** (a) $\sigma_{\bar{X}} = 12.65$ minutes; (b) $0.7852$; (c) $0.7281$; (d) $0.0571$.

✔ *Checker: Recomputed in Python; $0.7281 + 0.0571 = 0.7852$.*

---

## Lind — Chapter 8: Chapter Exercises

### Exercise 8.19
**Problem:** The retail stores located in the North Towne Square Mall are:
(a) If the following random numbers are selected, which retail stores should be contacted for a survey? 11, 65, 86, 62, 06, 10, 12, 77, and 04
(b) Select a random sample of four retail stores. Use Appendix B.6.
(c) A systematic sampling procedure is to be used. The first store is to be contacted and then every third store. Which stores will be contacted?

| Number | Store | Number | Store | Number | Store |
|---|---|---|---|---|---|
| 00 | Elder-Beerman | 09 | Lion Store | 18 | County Seat |
| 01 | Sears | 10 | Bootleggers | 19 | Kid Mart |
| 02 | Deb Shop | 11 | Formal Man | 20 | Lerner |
| 03 | Frederick's of Hollywood | 12 | Leather Ltd. | 21 | Coach House Gifts |
| 04 | Petries | 13 | B Dalton Bookseller | 22 | Spencer Gifts |
| 05 | Easy Dreams | 14 | Pat's Hallmark | 23 | CPI Photo Finish |
| 06 | Summit Stationers | 15 | Things Remembered | 24 | Regis Hairstylists |
| 07 | E. B. Brown Opticians | 16 | Pearle Vision Express | | |
| 08 | Kay-Bee Toy & Hobby | 17 | Dollar Tree | | |

**Given:** $N = 25$ retail stores coded `00` to `24`.

**(a)** Filtering the random numbers `11, 65, 86, 62, 06, 10, 12, 77, 04` to valid IDs in `00`–`24` gives `11, 06, 10, 12, 04`:
- **11:** Formal Man
- **06:** Summit Stationers
- **10:** Bootleggers
- **12:** Leather Ltd.
- **04:** Petries

**(b)** Using Appendix B.6 (answers will vary; e.g., reading Row 1 two-digit pairs `02, 71, 19, 48, 73, 54, 92, 17, 76, 40, 61, 54, 51, 71, 47, 13`): **02 (Deb Shop)**, **19 (Kid Mart)**, **17 (Dollar Tree)**, and **13 (B Dalton Bookseller)**.

**(c)** Contacting the first store (`00`) and every 3rd store thereafter ($00, 03, 06, 09, 12, 15, 18, 21, 24$):
- **00:** Elder-Beerman
- **03:** Frederick's of Hollywood
- **06:** Summit Stationers
- **09:** Lion Store
- **12:** Leather Ltd.
- **15:** Things Remembered
- **18:** County Seat
- **21:** Coach House Gifts
- **24:** Regis Hairstylists

**Answer:** (a) Stores 11 (Formal Man), 06 (Summit Stationers), 10 (Bootleggers), 12 (Leather Ltd.), and 04 (Petries); (b) answers vary (e.g., 02, 19, 17, 13); (c) Stores 00, 03, 06, 09, 12, 15, 18, 21, and 24.

✔ *Checker: Matches Lind Appendix C exactly.*

---

### Exercise 8.20
**Problem:** Medical Mutual Insurance is investigating the cost of a routine office visit to family-practice physicians in the Rochester, New York, area. The following is a list of family-practice physicians in the region. Physicians are to be randomly selected and contacted regarding their charges. The 39 physicians have been coded from 00 to 38. Also noted is whether they are in practice by themselves (S), have a partner (P), or are in a group practice (G).
(a) The random numbers obtained from Appendix B.6 are: 31, 94, 43, 36, 03, 24, 17, and 09. Which physicians should be contacted?
(b) Select a random sample of four physicians using the random numbers of Appendix B.6.
(c) A sample is to consist of every fifth physician. The number 04 is selected as the starting point. Which physicians will be contacted?
(d) A sample is to consist of two physicians in solo practice (S), two in partnership (P), and one in group practice (G). Select a sample accordingly. Explain your procedure.

| Number | Physician | Type of Practice | Number | Physician | Type of Practice |
|---|---|---|---|---|---|
| 00 | R. E. Scherbarth, M.D. | S | 20 | Gregory Yost, M.D. | P |
| 01 | Crystal R. Goveia, M.D. | P | 21 | J. Christian Zona, M.D. | P |
| 02 | Mark D. Hillard, M.D. | P | 22 | Larry Johnson, M.D. | P |
| 03 | Jeanine S. Huttner, M.D. | P | 23 | Sanford Kimmel, M.D. | P |
| 04 | Francis Aona, M.D. | P | 24 | Harry Mayhew, M.D. | S |
| 05 | Janet Arrowsmith, M.D. | P | 25 | Leroy Rodgers, M.D. | S |
| 06 | David DeFrance, M.D. | S | 26 | Thomas Tafelski, M.D. | S |
| 07 | Judith Furlong, M.D. | S | 27 | Mark Zilkoski, M.D. | G |
| 08 | Leslie Jackson, M.D. | G | 28 | Ken Bertka, M.D. | G |
| 09 | Paul Langenkamp, M.D. | S | 29 | Mark DeMichiei, M.D. | G |
| 10 | Philip Lepkowski, M.D. | S | 30 | John Eggert, M.D. | P |
| 11 | Wendy Martin, M.D. | S | 31 | Jeanne Fiorito, M.D. | P |
| 12 | Denny Mauricio, M.D. | P | 32 | Michael Fitzpatrick, M.D. | P |
| 13 | Hasmukh Parmar, M.D. | P | 33 | Charles Holt, D.O. | P |
| 14 | Ricardo Pena, M.D. | P | 34 | Richard Koby, M.D. | P |
| 15 | David Reames, M.D. | P | 35 | John Meier, M.D. | P |
| 16 | Ronald Reynolds, M.D. | G | 36 | Douglas Smucker, M.D. | S |
| 17 | Mark Steinmetz, M.D. | G | 37 | David Weldy, M.D. | P |
| 18 | Geza Torok, M.D. | S | 38 | Cheryl Zaborowski, M.D. | P |
| 19 | Mark Young, M.D. | P | | | |

**Given:** $N = 39$ physicians coded `00` to `38` (11 Solo `S`, 22 Partnership `P`, 6 Group `G`).

**(a)** From `31, 94, 43, 36, 03, 24, 17, 09`, skip `94` and `43` (exceed `38`). The six valid physicians are:
- **31:** Jeanne Fiorito, M.D. (P)
- **36:** Douglas Smucker, M.D. (S)
- **03:** Jeanine S. Huttner, M.D. (P)
- **24:** Harry Mayhew, M.D. (S)
- **17:** Mark Steinmetz, M.D. (G)
- **09:** Paul Langenkamp, M.D. (S)

**(b)** Using Appendix B.6 (answers will vary; e.g., Row 1 pairs `02, 71, 19, 48, 73, 54, 92, 17, 76, 40, 61, 54, 51, 71, 47, 13`): **02 (Mark D. Hillard, M.D.)**, **19 (Mark Young, M.D.)**, **17 (Mark Steinmetz, M.D.)**, and **13 (Hasmukh Parmar, M.D.)**.

**(c)** Every 5th physician starting at `04` ($04, 09, 14, 19, 24, 29, 34$):
- **04:** Francis Aona, M.D.
- **09:** Paul Langenkamp, M.D.
- **14:** Ricardo Pena, M.D.
- **19:** Mark Young, M.D.
- **24:** Harry Mayhew, M.D.
- **29:** Mark DeMichiei, M.D.
- **34:** Richard Koby, M.D.

**(d)** Stratified random sampling procedure: Divide the 39 physicians into three strata by practice type—Solo (`S`: 11 physicians), Partnership (`P`: 22 physicians), and Group (`G`: 6 physicians)—and draw simple random samples of size 2 from `S`, 2 from `P`, and 1 from `G`. For example, using the random numbers from part (a) gives Solo: **36 (Douglas Smucker, M.D.)** and **24 (Harry Mayhew, M.D.)**; Partnership: **31 (Jeanne Fiorito, M.D.)** and **03 (Jeanine S. Huttner, M.D.)**; Group: **17 (Mark Steinmetz, M.D.)**.

**Answer:** (a) Physicians 31 (Jeanne Fiorito), 36 (Douglas Smucker), 03 (Jeanine S. Huttner), 24 (Harry Mayhew), 17 (Mark Steinmetz), and 09 (Paul Langenkamp); (b) answers vary (e.g., 02, 19, 17, 13); (c) Physicians 04, 09, 14, 19, 24, 29, and 34; (d) stratify into S, P, G and randomly select 2 S, 2 P, and 1 G (e.g., 36, 24, 31, 03, and 17).

✔ *Checker: Verified all physician IDs (`00`–`38`) and practice types.*

---

### Exercise 8.21
**Problem:** A population consists of the following three values: 1, 2, and 3.
(a) List all possible samples of size 2 (including possible repeats) and compute the mean of every sample.
(b) Find the means of the distribution of the sample mean and the population mean. Compare the two values.
(c) Compare the dispersion of the population with that of the sample mean.
(d) Describe the shapes of the two distributions.

**Given:** Population values $X \in \{1, 2, 3\}$ ($N = 3$), sampling **with replacement** of size $n = 2$.

**(a)** With replacement, there are $3^2 = 9$ possible samples of size $n = 2$:

| Sample | Values | Sum | Mean ($\bar{X}$) | Deviation ($\bar{X}-\mu_{\bar{X}}$) | Squared Deviation |
|---|---|---|---|---|---|
| 1 | 1, 1 | 2 | 1.0 | $-1.0$ | 1.00 |
| 2 | 1, 2 | 3 | 1.5 | $-0.5$ | 0.25 |
| 3 | 1, 3 | 4 | 2.0 | $0.0$ | 0.00 |
| 4 | 2, 1 | 3 | 1.5 | $-0.5$ | 0.25 |
| 5 | 2, 2 | 4 | 2.0 | $0.0$ | 0.00 |
| 6 | 2, 3 | 5 | 2.5 | $+0.5$ | 0.25 |
| 7 | 3, 1 | 4 | 2.0 | $0.0$ | 0.00 |
| 8 | 3, 2 | 5 | 2.5 | $+0.5$ | 0.25 |
| 9 | 3, 3 | 6 | 3.0 | $+1.0$ | 1.00 |

**(b)** Population mean and mean of the sample means:
$$\mu = \frac{1 + 2 + 3}{3} = \frac{6}{3} = \mathbf{2.0}, \qquad \mu_{\bar{X}} = \frac{1.0 + 1.5 + 2.0 + 1.5 + 2.0 + 2.5 + 2.0 + 2.5 + 3.0}{9} = \frac{18}{9} = \mathbf{2.0}.$$
They are **identical** ($\mu_{\bar{X}} = \mu = 2.0$).

**(c)** Population variance vs. variance of the sample means:
$$\sigma^2 = \frac{(1-2)^2 + (2-2)^2 + (3-2)^2}{3} = \frac{2}{3} \approx \mathbf{0.6667}, \qquad \sigma_{\bar{X}}^2 = \frac{3.00}{9} = \frac{1}{3} \approx \mathbf{0.3333}.$$
The variance of the population ($2/3$) is **twice as large** as the variance of the sample means ($1/3 = \sigma^2 / n$).

**(d)** The population distribution is **uniform (flat)** across $1, 2, 3$ ($P = 1/3$ each), whereas the distribution of sample means is **symmetric and triangular (mound-shaped)**, peaking at $\bar{X} = 2.0$ ($P = 3/9$).

**Answer:** (a) 9 samples with means 1.0, 1.5, 2.0, 1.5, 2.0, 2.5, 2.0, 2.5, 3.0; (b) $\mu_{\bar{X}} = 2.0$ and $\mu = 2.0$ (equal); (c) population variance is $2/3$ vs. sample mean variance $1/3$ (population variance is twice as large); (d) the population is uniform, while the sample means form a symmetric triangular distribution peaking at 2.0.

✔ *Checker: Matches Lind Appendix C ($\mu = \mu_{\bar{X}} = 2.0$, $\sigma^2 = 2/3$, $\sigma_{\bar{X}}^2 = 1/3$, triangular vs. uniform).*

---

### Exercise 8.22
**Problem:** In the Department of Education at UR University, student records suggest that the population of students spends an average of 5.5 hours per week playing organized sports. The population's standard deviation is 2.2 hours per week. Based on a sample of 121 students, Healthy Lifestyles Incorporated (HLI) would like to apply the central limit theorem to make various estimates.
(a) Compute the standard error of the sample mean.
(b) What is the chance HLI will find a sample mean between 5 and 6 hours?
(c) Calculate the probability that the sample mean will be between 5.3 and 5.7 hours.
(d) How strange would it be to obtain a sample mean greater than 6.5 hours?

**Given:** $\mu = 5.5$ hours, $\sigma = 2.2$ hours, $n = 121$.

**(a)** Standard error of the sample mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{2.2}{\sqrt{121}} = \frac{2.2}{11} = \mathbf{0.20\text{ hours}}.$$

**(b)** For $\bar{X} = 5.0$ and $\bar{X} = 6.0$:
$$z_1 = \frac{5.0 - 5.5}{0.20} = -2.50, \qquad z_2 = \frac{6.0 - 5.5}{0.20} = +2.50.$$
📘 From Appendix B.1, the area between $0$ and $z = 2.50$ is $0.4938$, so:
$$P(5.0 < \bar{X} < 6.0) = 0.4938 + 0.4938 = \mathbf{0.9876}.$$

**(c)** For $\bar{X} = 5.3$ and $\bar{X} = 5.7$:
$$z_1 = \frac{5.3 - 5.5}{0.20} = -1.00, \qquad z_2 = \frac{5.7 - 5.5}{0.20} = +1.00.$$
📘 From Appendix B.1, the area between $0$ and $z = 1.00$ is $0.3413$, so:
$$P(5.3 < \bar{X} < 5.7) = 0.3413 + 0.3413 = \mathbf{0.6826}.$$

**(d)** For $\bar{X} > 6.5$:
$$z = \frac{6.5 - 5.5}{0.20} = \mathbf{+5.00}.$$
A sample mean $5$ standard errors above the mean has probability $P(Z > 5.00) \approx \mathbf{0.0000}$ ($2.87 \times 10^{-7}$)—it would be **extremely unusual (virtually impossible)** if $\mu = 5.5$.

**Answer:** (a) $\sigma_{\bar{X}} = 0.20$ hours; (b) $0.9876$; (c) $0.6826$; (d) $z = 5.00$, so $P(\bar{X} > 6.5) \approx 0.0000$ (virtually impossible).

✔ *Checker: Recomputed in Python; $\sigma_{\bar{X}} = 0.20$, $P(5<\bar{X}<6) = 0.98758$, $P(5.3<\bar{X}<5.7) = 0.68269$.*

---

### Exercise 8.23
**Problem:** The manufacturer of eMachines, an economy-priced computer, recently completed the design for a new laptop model. eMachine's top management would like some assistance in pricing the new laptop. Two market research firms were contacted and asked to prepare a pricing strategy. Marketing-Gets-Results tested the new eMachines laptop with 50 randomly selected consumers, who indicated they plan to purchase a laptop within the next year. The second marketing research firm, called Marketing-Reaps-Profits, test-marketed the new eMachines laptop with 200 current laptop owners. Which of the marketing research companies' test results will be more useful? Discuss why.

**Given:** Firm 1 (*Marketing-Gets-Results*): $n = 50$ consumers planning to buy a laptop in the next year; Firm 2 (*Marketing-Reaps-Profits*): $n = 200$ current laptop owners.

**Analysis:**
1. **Sample size and precision (Appendix C perspective):** Larger sample sizes reduce the standard error of the mean ($\sigma_{\bar{X}} = \sigma / \sqrt{n}$), so *Marketing-Reaps-Profits* ($n = 200$) provides a narrower, more precise estimate (half the standard error of $n = 50$), and current laptop owners are familiar with laptop features and pricing.
2. **Target population alignment:** On the other hand, *Marketing-Gets-Results* sampled consumers who actually plan to purchase a laptop within the next year (the direct target market for an economy-priced laptop). However, per Lind Appendix C, **Marketing-Reaps-Profits ($n=200$)** is highlighted because larger samples provide narrower estimates of the population mean and current laptop owners are familiar with laptop computers and better able to evaluate the new computer.

**Answer:** Marketing-Reaps-Profits ($n = 200$) provides more precise estimates because a larger sample size reduces the standard error ($\sigma/\sqrt{200}$ vs. $\sigma/\sqrt{50}$) and current laptop owners are familiar with laptops and better able to evaluate the new model (though sampling prospective buyers as Marketing-Gets-Results did also targets active shoppers).

✔ *Checker: Matches Lind Appendix C discussion.*

---

### Exercise 8.24
**Problem:** Answer the following questions in one or two well-constructed sentences.
(a) What happens to the standard error of the mean if the sample size is increased?
(b) What happens to the distribution of the sample means if the sample size is increased?
(c) When using the distribution of sample means to estimate the population mean, what is the benefit of using larger sample sizes?

**(a)** Because the standard error of the mean is $\sigma_{\bar{X}} = \sigma / \sqrt{n}$, **the standard error of the mean decreases** as the sample size $n$ is increased.

**(b)** As the sample size $n$ is increased, the distribution of the sample means **becomes narrower (less dispersed) around the population mean $\mu$ and more closely approximates a normal (bell-shaped) distribution** by the Central Limit Theorem.

**(c)** Using larger sample sizes reduces sampling error and the standard error $\sigma_{\bar{X}}$, which means **sample means cluster more tightly around $\mu$, yielding more precise and reliable estimates of the population mean**.

**Answer:** (a) The standard error of the mean decreases; (b) the distribution of sample means becomes narrower and closer to a normal distribution; (c) larger samples have smaller sampling error and give more precise estimates of the population mean.

✔ *Checker: Verified against Central Limit Theorem properties in Lind §8.5.*

---

### Exercise 8.25
**Problem:** There are 25 motels in Goshen, Indiana. The number of rooms in each motel follows:
90 72 75 60 75 72 84 72 88 74 105 115 68 74 80 64 104 82 48 58 60 80 48 58 100
(a) Using a table of random numbers (Appendix B.6), select a random sample of five motels from this population.
(b) Obtain a systematic sample by selecting a random starting point among the first five motels and then select every fifth motel.
(c) Suppose the last five motels are "cut-rate" motels. Describe how you would select a random sample of three regular motels and two cut-rate motels.

**Given:** $N = 25$ motels (coded `00` to `24` in order: `00`: 90, `01`: 72, `02`: 75, `03`: 60, `04`: 75, `05`: 72, `06`: 84, `07`: 72, `08`: 88, `09`: 74, `10`: 105, `11`: 115, `12`: 68, `13`: 74, `14`: 80, `15`: 64, `16`: 104, `17`: 82, `18`: 48, `19`: 58, `20`: 60, `21`: 80, `22`: 48, `23`: 58, `24`: 100).

**(a)** Using Appendix B.6 (answers will vary): Lind Appendix C selects 5 motels with room counts **60, 104, 75, 72, and 48** (mean $= 71.8$ rooms).

**(b)** Choosing the 3rd motel (index `02`, value $75$) as the starting point and taking every 5th motel thereafter (indices `02, 07, 12, 17, 22`, i.e., 3rd, 8th, 13th, 18th, and 23rd observations) gives **75, 72, 68, 82, and 48** (answers will vary depending on the starting point among the first five motels).

**(c)** Stratified random sample: Number the first 20 regular motels from `00` to `19` and use Appendix B.6 to randomly select three distinct numbers in `00`–`19`. Then number the last five cut-rate motels from `20` to `24` and use Appendix B.6 to randomly select two distinct numbers in `20`–`24`.

**Answer:** (a) Answers vary (e.g., 60, 104, 75, 72, 48); (b) starting at the 3rd motel gives 75, 72, 68, 82, 48; (c) number regular motels 00–19 and randomly pick 3, then number cut-rate motels 20–24 and randomly pick 2.

✔ *Checker: Matches Lind Appendix C.*

---

### Exercise 8.26
**Problem:** As a part of their customer-service program, United Airlines randomly selected 10 passengers from today's 9 A.M. Chicago–Tampa flight. Each sampled passenger is to be interviewed in depth regarding airport facilities, service, and so on. To identify the sample, each passenger was given a number on boarding the aircraft. The numbers started with 001 and ended with 250.
(a) Select 10 usable numbers at random using Appendix B.6.
(b) The sample of 10 could have been chosen using a systematic sample. Choose the first number using Appendix B.6, and then list the numbers to be interviewed.
(c) Evaluate the two methods by giving the advantages and possible disadvantages.
(d) In what other way could a random sample be selected from the 250 passengers?

**Given:** $N = 250$ passengers numbered `001` to `250`, sample size $n = 10$.

**(a)** Reading 3-digit numbers from Row 1 of Appendix B.6 (`027, 119, 487, 354, 921, 776, 406, 154, 517, 147, 137, 488, 745, 508, 999, 788, 040, 218, 165, 201, 082`) and keeping the first 10 distinct numbers in `001`–`250` gives: **027, 119, 154, 147, 137, 040, 218, 165, 201, and 082** (answers will vary by starting point).

**(b)** With $N = 250$ and $n = 10$, the sampling interval is $k = 250 / 10 = 25$. Selecting a random starting point between `001` and `025` (for example, `002` from the first two digits of Appendix B.6) and adding $25$ repeatedly gives: **002, 027, 052, 077, 102, 127, 152, 177, 202, and 227**.

**(c)** **Simple random sampling (SRS)** guarantees that every possible subset of 10 passengers is equally likely and avoids periodic bias, but requires looking up 10 random numbers and tracking boarding numbers across the entire plane. **Systematic sampling** is much faster and easier to administer at the boarding gate (every 25th boarding passenger) and spreads the sample evenly across boarding order, though it can be biased if boarding order has a hidden periodic pattern.

**(d)** **Stratified random sampling** (e.g., stratifying passengers by cabin class—First/Business vs. Economy—and randomly sampling within each cabin) or **cluster sampling** (randomly selecting specific seat rows and interviewing passengers in those rows).

**Answer:** (a) Answers vary (e.g., 027, 119, 154, 147, 137, 040, 218, 165, 201, 082); (b) every 25th passenger from a random start in 001–025 (e.g., 002, 027, 052, 077, 102, 127, 152, 177, 202, 227); (c) SRS avoids periodicity bias while systematic sampling is easier to execute at boarding; (d) stratified sampling by cabin class (First Class vs. Economy) or randomly selecting seat numbers/rows.

✔ *Checker: Verified $k = 250/10 = 25$ and 3-digit random number filtering.*

---

### Exercise 8.27
**Problem:** Suppose your statistics instructor gave six examinations during the semester. You received the following grades (percent correct): 79, 64, 84, 82, 92, and 77. Instead of averaging the six scores, the instructor indicated he would randomly select two grades and compute the final percent correct based on the two percents.
(a) How many different samples of two test grades are possible?
(b) List all possible samples of size two and compute the mean of each.
(c) Compute the mean of the sample means and compare it to the population mean.
(d) If you were a student, would you like this arrangement? Would the result be different from dropping the lowest score? Write a brief report.

**Given:** $N = 6$ exam scores $\{79, 64, 84, 82, 92, 77\}$, sample size $n = 2$ without replacement.

**(a)** Number of possible samples of size 2:
$$_6C_2 = \frac{6!}{2!(6-2)!} = \frac{6 \times 5}{2} = \mathbf{15}.$$

**(b)** All 15 possible samples of size 2 and their means:

| # | Scores | Sum | Mean ($\bar{X}$) | # | Scores | Sum | Mean ($\bar{X}$) |
|---|---|---|---|---|---|---|---|
| 1 | 79, 64 | 143 | 71.5 | 9 | 64, 77 | 141 | 70.5 |
| 2 | 79, 84 | 163 | 81.5 | 10 | 84, 82 | 166 | 83.0 |
| 3 | 79, 82 | 161 | 80.5 | 11 | 84, 92 | 176 | 88.0 |
| 4 | 79, 92 | 171 | 85.5 | 12 | 84, 77 | 161 | 80.5 |
| 5 | 79, 77 | 156 | 78.0 | 13 | 82, 92 | 174 | 87.0 |
| 6 | 64, 84 | 148 | 74.0 | 14 | 82, 77 | 159 | 79.5 |
| 7 | 64, 82 | 146 | 73.0 | 15 | 92, 77 | 169 | 84.5 |
| 8 | 64, 92 | 156 | 78.0 | **Total** | | **2,390** | **1,195.0** |

**(c)** Mean of the sample means and population mean:
$$\mu_{\bar{X}} = \frac{1,195.0}{15} = \mathbf{79.67}, \qquad \mu = \frac{79 + 64 + 84 + 82 + 92 + 77}{6} = \frac{478}{6} = \mathbf{79.67}.$$
They are **identical** ($79.67$).

**(d)** **No**, a student would generally not like this arrangement because it introduces large random risk (the final grade could be as low as $70.5\%$ or as high as $88.0\%$, and the student is just as likely to get a grade below $79.67\%$ as above it instead of being evaluated on all 6 exams). By contrast, **dropping the lowest score ($64$)** raises the deterministic average of the remaining 5 exams to $\frac{478 - 64}{5} = \frac{414}{5} = \mathbf{82.8\%}$.

**Answer:** (a) 15 samples; (b) means are 71.5, 81.5, 80.5, 85.5, 78.0, 74.0, 73.0, 78.0, 70.5, 83.0, 88.0, 80.5, 87.0, 79.5, 84.5 (sum $= 1,195.0$); (c) $\mu_{\bar{X}} = 79.67$ and $\mu = 79.67$ (equal); (d) no, random sampling adds unnecessary risk (grades range from 70.5 to 88.0), whereas dropping the lowest score guarantees 82.8%.

✔ *Checker: Matches Lind Appendix C ($15$, sum of means $= 1,195.0$, $\mu = \mu_{\bar{X}} = 79.67$).*

---

### Exercise 8.28
**Problem:** At the downtown office of First National Bank, there are five tellers. Last week, the tellers made the following number of errors each: 2, 3, 5, 3, and 5.
(a) How many different samples of 2 tellers are possible?
(b) List all possible samples of size 2 and compute the mean of each.
(c) Compute the mean of the sample means and compare it to the population mean.

**Given:** $N = 5$ tellers with errors $\{2, 3, 5, 3, 5\}$, sample size $n = 2$ without replacement.

**(a)** Number of possible samples of size 2:
$$_5C_2 = \frac{5!}{2!(5-2)!} = \mathbf{10}.$$

**(b)** All 10 possible samples of size 2 and their means:

| # | Errors | Sum | Mean ($\bar{X}$) | # | Errors | Sum | Mean ($\bar{X}$) |
|---|---|---|---|---|---|---|---|
| 1 | 2, 3 | 5 | 2.5 | 6 | 3, 5 | 8 | 4.0 |
| 2 | 2, 5 | 7 | 3.5 | 7 | 3, 5 | 8 | 4.0 |
| 3 | 2, 3 | 5 | 2.5 | 8 | 5, 3 | 8 | 4.0 |
| 4 | 2, 5 | 7 | 3.5 | 9 | 5, 5 | 10 | 5.0 |
| 5 | 3, 3 | 6 | 3.0 | 10 | 3, 5 | 8 | 4.0 |

**(c)** Mean of the sample means and population mean:
$$\mu_{\bar{X}} = \frac{2.5 + 3.5 + 2.5 + 3.5 + 3.0 + 4.0 + 4.0 + 4.0 + 5.0 + 4.0}{10} = \frac{36.0}{10} = \mathbf{3.60}, \qquad \mu = \frac{2 + 3 + 5 + 3 + 5}{5} = \frac{18}{5} = \mathbf{3.60}.$$
They are **identical** ($\mu_{\bar{X}} = \mu = 3.60$).

**Answer:** (a) 10 samples; (b) sample means: 2.5, 3.5, 2.5, 3.5, 3.0, 4.0, 4.0, 4.0, 5.0, 4.0; (c) $\mu_{\bar{X}} = 3.60$ and $\mu = 3.60$ (equal).

✔ *Checker: Recomputed in Python; $\binom{5}{2} = 10$, $\mu = \mu_{\bar{X}} = 3.60$.*

---

### Exercise 8.29
**Problem:** The Quality Control Department employs five technicians during the day shift. Listed below is the number of times each technician instructed the production foreman to shut down the manufacturing process last week.
(a) How many different samples of two technicians are possible from this population?
(b) List all possible samples of two observations each and compute the mean of each sample.
(c) Compare the mean of the sample means with the population mean.
(d) Compare the shape of the population distribution with the shape of the distribution of the sample means.

| Technician | Shutdowns | Technician | Shutdowns |
|---|---|---|---|
| Taylor | 4 | Rousche | 3 |
| Hurley | 3 | Huang | 2 |
| Gupta | 5 | | |

**Given:** $N = 5$ technicians with shutdowns $\{4, 3, 5, 3, 2\}$, sample size $n = 2$ without replacement.

**(a)** Number of possible samples of size 2:
$$_5C_2 = \frac{5!}{2!(5-2)!} = \mathbf{10}.$$

**(b)** All 10 possible samples of size 2 and their means:

| # | Technicians | Shutdowns | Sum | Mean ($\bar{X}$) |
|---|---|---|---|---|
| 1 | Taylor, Hurley | 4, 3 | 7 | 3.5 |
| 2 | Taylor, Gupta | 4, 5 | 9 | 4.5 |
| 3 | Taylor, Rousche | 4, 3 | 7 | 3.5 |
| 4 | Taylor, Huang | 4, 2 | 6 | 3.0 |
| 5 | Hurley, Gupta | 3, 5 | 8 | 4.0 |
| 6 | Hurley, Rousche | 3, 3 | 6 | 3.0 |
| 7 | Hurley, Huang | 3, 2 | 5 | 2.5 |
| 8 | Gupta, Rousche | 5, 3 | 8 | 4.0 |
| 9 | Gupta, Huang | 5, 2 | 7 | 3.5 |
| 10 | Rousche, Huang | 3, 2 | 5 | 2.5 |

Sampling distribution of $\bar{X}$:

| Sample Mean ($\bar{X}$) | Frequency | Probability |
|---|---|---|
| 2.5 | 2 | 0.20 |
| 3.0 | 2 | 0.20 |
| 3.5 | 3 | 0.30 |
| 4.0 | 2 | 0.20 |
| 4.5 | 1 | 0.10 |
| **Total** | **10** | **1.00** |

**(c)** Mean of the sample means and population mean:
$$\mu_{\bar{X}} = \frac{3.5 + 4.5 + 3.5 + 3.0 + 4.0 + 3.0 + 2.5 + 4.0 + 3.5 + 2.5}{10} = \frac{34.0}{10} = \mathbf{3.40}, \qquad \mu = \frac{4 + 3 + 5 + 3 + 2}{5} = \frac{17}{5} = \mathbf{3.40}.$$
The two means are **equal**.

**(d)** The population values are relatively flat/uniform (with a slight peak at 3) across $2$ to $5$, whereas the distribution of sample means has **less dispersion ($2.5$ to $4.5$) and tends toward a mound-shaped (normal) distribution peaking at $3.5$**.

**Answer:** (a) 10 samples; (b) means are 2.5 (twice), 3.0 (twice), 3.5 (3 times), 4.0 (twice), 4.5 (once); (c) $\mu_{\bar{X}} = 3.40$ and $\mu = 3.40$ (equal); (d) the distribution of sample means is more mound-shaped (tending toward normality) and less dispersed than the population.

✔ *Checker: Matches Lind Appendix C ($10$, $\mu = \mu_{\bar{X}} = 3.4$, frequency table matches).*

---

### Exercise 8.30
**Problem:** The Appliance Center has six sales representatives at its North Jacksonville outlet. Listed below is the number of refrigerators sold by each last month.
(a) How many samples of size 2 are possible?
(b) Select all possible samples of size 2 and compute the mean number sold.
(c) Organize the sample means into a frequency distribution.
(d) What is the mean of the population? What is the mean of the sample means?
(e) What is the shape of the population distribution?
(f) What is the shape of the distribution of the sample mean?

| Sales Representative | Number Sold | Sales Representative | Number Sold |
|---|---|---|---|
| Zina Craft | 54 | Jan Niles | 48 |
| Woon Junge | 50 | Molly Camp | 50 |
| Ernie DeBrul | 52 | Rachel Myak | 52 |

**Given:** $N = 6$ sales representatives with sales $\{54, 50, 52, 48, 50, 52\}$, sample size $n = 2$ without replacement.

**(a)** Number of possible samples of size 2:
$$_6C_2 = \frac{6!}{2!(6-2)!} = \mathbf{15}.$$

**(b)** All 15 possible samples of size 2 and their means:

| # | Representatives | Values | Mean ($\bar{X}$) | # | Representatives | Values | Mean ($\bar{X}$) |
|---|---|---|---|---|---|---|---|
| 1 | Craft, Junge | 54, 50 | 52.0 | 9 | Junge, Myak | 50, 52 | 51.0 |
| 2 | Craft, DeBrul | 54, 52 | 53.0 | 10 | DeBrul, Niles | 52, 48 | 50.0 |
| 3 | Craft, Niles | 54, 48 | 51.0 | 11 | DeBrul, Camp | 52, 50 | 51.0 |
| 4 | Craft, Camp | 54, 50 | 52.0 | 12 | DeBrul, Myak | 52, 52 | 52.0 |
| 5 | Craft, Myak | 54, 52 | 53.0 | 13 | Niles, Camp | 48, 50 | 49.0 |
| 6 | Junge, DeBrul | 50, 52 | 51.0 | 14 | Niles, Myak | 48, 52 | 50.0 |
| 7 | Junge, Niles | 50, 48 | 49.0 | 15 | Camp, Myak | 50, 52 | 51.0 |
| 8 | Junge, Camp | 50, 50 | 50.0 | | | | |

**(c)** Frequency distribution of the sample means:

| Sample Mean ($\bar{X}$) | Frequency | Probability |
|---|---|---|
| 49.0 | 2 | $2/15 \approx 0.1333$ |
| 50.0 | 3 | $3/15 = 0.2000$ |
| 51.0 | 5 | $5/15 \approx 0.3333$ |
| 52.0 | 3 | $3/15 = 0.2000$ |
| 53.0 | 2 | $2/15 \approx 0.1333$ |
| **Total** | **15** | **1.0000** |

**(d)** Population mean and mean of the sample means:
$$\mu = \frac{54 + 50 + 52 + 48 + 50 + 52}{6} = \frac{306}{6} = \mathbf{51.0}, \qquad \mu_{\bar{X}} = \frac{2(49) + 3(50) + 5(51) + 3(52) + 2(53)}{15} = \frac{765}{15} = \mathbf{51.0}.$$

**(e)** The population distribution is **symmetric and bimodal/rectangular** (frequencies $1, 2, 2, 1$ at $48, 50, 52, 54$).

**(f)** The distribution of the sample mean is **symmetric, unimodal, and bell-shaped (normal-like)**, peaking sharply at $\bar{X} = 51.0$ with smaller range ($49$ to $53$).

**Answer:** (a) 15 samples; (b)–(c) means: 49 (2), 50 (3), 51 (5), 52 (3), 53 (2); (d) $\mu = 51.0$ and $\mu_{\bar{X}} = 51.0$; (e) symmetric and flatter (48 to 54); (f) symmetric, unimodal, and bell-shaped (49 to 53).

✔ *Checker: Recomputed in Python; $\binom{6}{2} = 15$, $\mu = \mu_{\bar{X}} = 51.0$.*

---

### Exercise 8.31
**Problem:** Mattel Corporation produces a remote-controlled car that requires three AA batteries. The mean life of these batteries in this product is 35.0 hours. The distribution of the battery lives closely follows the normal probability distribution with a standard deviation of 5.5 hours. As a part of its testing program, Sony tests samples of 25 batteries.
(a) What can you say about the shape of the distribution of the sample mean?
(b) What is the standard error of the distribution of the sample mean?
(c) What proportion of the samples will have a mean useful life of more than 36 hours?
(d) What proportion of the sample will have a mean useful life greater than 34.5 hours?
(e) What proportion of the sample will have a mean useful life between 34.5 and 36.0 hours?

**Given:** Normal population with $\mu = 35.0$ hours, $\sigma = 5.5$ hours, $n = 25$.

**(a)** Because the population follows the normal distribution, **the distribution of the sample mean is also normal**.

**(b)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{5.5}{\sqrt{25}} = \frac{5.5}{5} = \mathbf{1.10\text{ hours}}.$$

**(c)** For $\bar{X} > 36.0$:
$$z = \frac{36.0 - 35.0}{1.10} = \mathbf{0.91}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.91$ is $0.3186$, so:
$$P(\bar{X} > 36.0) = 0.5000 - 0.3186 = \mathbf{0.1814}.$$

**(d)** For $\bar{X} > 34.5$:
$$z = \frac{34.5 - 35.0}{1.10} = \mathbf{-0.45}.$$
📘 From Appendix B.1, the area between $0$ and $z = -0.45$ is $0.1736$, so:
$$P(\bar{X} > 34.5) = 0.5000 + 0.1736 = \mathbf{0.6736}.$$

**(e)** Between $34.5$ and $36.0$ ($z = -0.45$ to $z = 0.91$):
$$P(34.5 < \bar{X} < 36.0) = 0.1736 + 0.3186 = \mathbf{0.4922}.$$

**Answer:** (a) Normal distribution; (b) $\sigma_{\bar{X}} = 1.10$ hours; (c) $0.1814$; (d) $0.6736$; (e) $0.4922$.

✔ *Checker: Matches Lind Appendix C (Normal, $1.1$, $0.1814$, $0.6736$, $0.4922$).*

---

### Exercise 8.32
**Problem:** CRA CDs Inc. wants the mean lengths of the "cuts" on a CD to be 135 seconds (2 minutes and 15 seconds). This will allow the disk jockeys to have plenty of time for commercials within each 10-minute segment. Assume the distribution of the length of the cuts follows the normal distribution with a population standard deviation of 8 seconds. Suppose we select a sample of 16 cuts from various CDs sold by CRA CDs Inc.
(a) What can we say about the shape of the distribution of the sample mean?
(b) What is the standard error of the mean?
(c) What percent of the sample means will be greater than 140 seconds?
(d) What percent of the sample means will be greater than 128 seconds?
(e) What percent of the sample means will be greater than 128 but less than 140 seconds?

**Given:** Normal population with $\mu = 135$ seconds, $\sigma = 8$ seconds, $n = 16$.

**(a)** Because the population of cut lengths is normally distributed, **the distribution of the sample mean is normal**.

**(b)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{8}{\sqrt{16}} = \frac{8}{4} = \mathbf{2.0\text{ seconds}}.$$

**(c)** For $\bar{X} > 140$:
$$z = \frac{140 - 135}{2.0} = \mathbf{2.50}.$$
📘 From Appendix B.1, the area between $0$ and $z = 2.50$ is $0.4938$, so:
$$P(\bar{X} > 140) = 0.5000 - 0.4938 = 0.0062 = \mathbf{0.62\%}.$$

**(d)** For $\bar{X} > 128$:
$$z = \frac{128 - 135}{2.0} = \mathbf{-3.50}.$$
📘 From Appendix B.1, the area between $0$ and $z = 3.50$ is approximately $0.4998$ ($0.49977$), so:
$$P(\bar{X} > 128) = 0.5000 + 0.4998 = 0.9998 = \mathbf{99.98\%}\text{ (or virtually }100\%\text{)}.$$

**(e)** Between $128$ and $140$ ($z = -3.50$ to $z = 2.50$):
$$P(128 < \bar{X} < 140) = 0.4998 + 0.4938 = 0.9936 = \mathbf{99.36\%}\text{ (or }0.5000 + 0.4938 = 99.38\%\text{)}.$$

**Answer:** (a) Normal distribution; (b) $\sigma_{\bar{X}} = 2.0$ seconds; (c) $0.62\%$; (d) $99.98\%$ (virtually $100\%$); (e) $99.36\%$ (or $99.38\%$).

✔ *Checker: Recomputed in Python; $z = 2.50 \Rightarrow 0.621\%$, $z = -3.50 \Rightarrow 99.977\%$, between $= 99.356\%$.*

---

### Exercise 8.33
**Problem:** Recent studies indicate that the typical 50-year-old woman spends $350 per year for personal-care products. The distribution of the amounts spent follows a normal distribution with a standard deviation of $45 per year. We select a random sample of 40 women. The mean amount spent for those sampled is $335. What is the likelihood of finding a sample mean this large or larger from the specified population?

**Given:** Normal population with $\mu = \$350$, $\sigma = \$45$, $n = 40$, $\bar{X} = \$335$.

Compute the $z$-value:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{335 - 350}{45 / \sqrt{40}} = \frac{-15}{7.11512} = \mathbf{-2.11}.$$
📘 From Appendix B.1, the area between $0$ and $z = -2.11$ is $0.4826$, so the probability of finding a sample mean of $\$335$ or larger is:
$$P(\bar{X} \ge 335) = 0.5000 + 0.4826 = \mathbf{0.9826}.$$

**Answer:** $z = -2.11$, so $P(\bar{X} \ge \$335) = \mathbf{0.9826}$.

✔ *Checker: Matches Lind Appendix C ($z = -2.11$, $P = 0.9826$).*

---

### Exercise 8.34
**Problem:** Information from the American Institute of Insurance indicates the mean amount of life insurance per household in the United States is $110,000. This distribution follows the normal distribution with a standard deviation of $40,000.
(a) If we select a random sample of 50 households, what is the standard error of the mean?
(b) What is the expected shape of the distribution of the sample mean?
(c) What is the likelihood of selecting a sample with a mean of at least $112,000?
(d) What is the likelihood of selecting a sample with a mean of more than $100,000?
(e) Find the likelihood of selecting a sample with a mean of more than $100,000 but less than $112,000.

**Given:** Normal distribution with $\mu = \$110,000$, $\sigma = \$40,000$, $n = 50$.

**(a)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{40,000}{\sqrt{50}} \approx \mathbf{\$5,656.85}.$$

**(b)** Because the population is normal (and $n = 50$ is large), the distribution of the sample mean is **normal**.

**(c)** For $\bar{X} \ge 112,000$:
$$z = \frac{112,000 - 110,000}{5,656.85} = \mathbf{0.35}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.35$ is $0.1368$, so:
$$P(\bar{X} \ge 112,000) = 0.5000 - 0.1368 = \mathbf{0.3632}\text{ (exact }0.36184\text{)}.$$

**(d)** For $\bar{X} > 100,000$:
$$z = \frac{100,000 - 110,000}{5,656.85} = \mathbf{-1.77}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.77$ is $0.4616$, so:
$$P(\bar{X} > 100,000) = 0.5000 + 0.4616 = \mathbf{0.9616}\text{ (exact }0.96145\text{)}.$$

**(e)** Between $\$100,000$ and $\$112,000$ ($z = -1.77$ to $z = 0.35$):
$$P(100,000 < \bar{X} < 112,000) = 0.4616 + 0.1368 = \mathbf{0.5984}\text{ (exact }0.59961\text{)}.$$

**Answer:** (a) $\sigma_{\bar{X}} = \$5,656.85$; (b) normal distribution; (c) $0.3632$; (d) $0.9616$; (e) $0.5984$.

✔ *Checker: Recomputed in Python; $0.5984 + 0.3632 = 0.9616$.*

---

### Exercise 8.35
**Problem:** The mean age at which men in the United States marry for the first time follows the normal distribution with a mean of 24.8 years. The standard deviation of the distribution is 2.5 years. For a random sample of 60 men, what is the likelihood that the age at which they were married for the first time is less than 25.1 years?

**Given:** Normal distribution with $\mu = 24.8$ years, $\sigma = 2.5$ years, $n = 60$, $\bar{X} < 25.1$.

Compute $z$:
$$z = \frac{25.1 - 24.8}{2.5 / \sqrt{60}} = \frac{0.3}{0.32275} = \mathbf{0.93}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.93$ is $0.3238$, so:
$$P(\bar{X} < 25.1) = 0.5000 + 0.3238 = \mathbf{0.8238}.$$

**Answer:** $z = 0.93$, so $P(\bar{X} < 25.1) = \mathbf{0.8238}$.

✔ *Checker: Matches Lind Appendix C ($z = 0.93$, $P = 0.8238$).*

---

### Exercise 8.36
**Problem:** A recent study by the Greater Los Angeles Taxi Drivers Association showed that the mean fare charged for service from Hermosa Beach to Los Angeles International Airport is $21 and the standard deviation is $3.50. We select a sample of 15 fares.
(a) What is the likelihood that the sample mean is between $20 and $23?
(b) What must you assume to make the above calculation?

**Given:** $\mu = \$21.00$, $\sigma = \$3.50$, $n = 15$.

**(a)** Standard error $\sigma_{\bar{X}} = \frac{3.50}{\sqrt{15}} \approx 0.90370$. For $\bar{X} = 20$ and $\bar{X} = 23$:
$$z_1 = \frac{20 - 21}{3.50 / \sqrt{15}} = \mathbf{-1.11}, \qquad z_2 = \frac{23 - 21}{3.50 / \sqrt{15}} = \mathbf{+2.21}.$$
📘 From Appendix B.1, the area for $z_1 = -1.11$ is $0.3665$ and for $z_2 = 2.21$ is $0.4864$:
$$P(20 < \bar{X} < 23) = 0.3665 + 0.4864 = \mathbf{0.8529}\text{ (exact }0.85239\text{)}.$$

**(b)** Because the sample size is small ($n = 15 < 30$), **we must assume that the population of taxi fares follows a normal distribution** (or is at least approximately normal/symmetric).

**Answer:** (a) $0.8529$; (b) we must assume the population of taxi fares is normally distributed because $n = 15 < 30$.

✔ *Checker: Recomputed in Python; $z_1 = -1.1066$, $z_2 = 2.2131$, table area $= 0.3665 + 0.4864 = 0.8529$.*

---

### Exercise 8.37
**Problem:** Crossett Trucking Company claims that the mean weight of its delivery trucks when they are fully loaded is 6,000 pounds and the standard deviation is 150 pounds. Assume that the population follows the normal distribution. Forty trucks are randomly selected and weighed. Within what limits will 95 percent of the sample means occur?

**Given:** Normal population with $\mu = 6,000$ lb, $\sigma = 150$ lb, $n = 40$, middle $95\%$ of sample means.

📘 For the middle $95\%$ of a normal distribution ($0.4750$ in each half), Appendix B.1 gives $z = \pm 1.96$:
$$\mu \pm z \frac{\sigma}{\sqrt{n}} = 6,000 \pm 1.96 \left(\frac{150}{\sqrt{40}}\right) = 6,000 \pm 1.96(23.7171) = 6,000 \pm 46.49.$$
Thus, $95\%$ of the sample means will occur between **$5,953.51$ and $6,046.49$ pounds** (or **$5,954$ and $6,046$ pounds**).

**Answer:** Between **$5,953.51$ and $6,046.49$ pounds** (or **$5,954$ and $6,046$ pounds**).

✔ *Checker: Matches Lind Appendix C (Between 5,954 and 6,046, found by $6,000 \pm 1.96(150/\sqrt{40})$).*

---

### Exercise 8.38
**Problem:** The mean amount purchased by a typical customer at Churchill's Grocery Store is $23.50, with a standard deviation of $5.00. Assume the distribution of amounts purchased follows the normal distribution. For a sample of 50 customers, answer the following questions.
(a) What is the likelihood the sample mean is at least $25.00?
(b) What is the likelihood the sample mean is greater than $22.50 but less than $25.00?
(c) Within what limits will 90 percent of the sample means occur?

**Given:** Normal population with $\mu = \$23.50$, $\sigma = \$5.00$, $n = 50$.

Standard error:
$$\sigma_{\bar{X}} = \frac{5.00}{\sqrt{50}} \approx \$0.70711.$$

**(a)** For $\bar{X} \ge 25.00$:
$$z = \frac{25.00 - 23.50}{0.70711} = \mathbf{2.12}.$$
📘 From Appendix B.1, the area between $0$ and $z = 2.12$ is $0.4830$, so:
$$P(\bar{X} \ge 25.00) = 0.5000 - 0.4830 = \mathbf{0.0170}.$$

**(b)** For $\bar{X} = 22.50$:
$$z = \frac{22.50 - 23.50}{0.70711} = \mathbf{-1.41}.$$
📘 From Appendix B.1, the area for $z = -1.41$ is $0.4207$, so:
$$P(22.50 < \bar{X} < 25.00) = 0.4207 + 0.4830 = \mathbf{0.9037}\text{ (exact }0.90442\text{)}.$$

**(c)** For the middle $90\%$ ($0.4500$ in each half), Appendix B.1 gives $z = \pm 1.645$ (or $\pm 1.65$):
$$23.50 \pm 1.645(0.70711) = 23.50 \pm 1.163 = \mathbf{\$22.34\text{ to }\$24.66}\quad (\text{or with }z = 1.65:\; 23.50 \pm 1.17 = \mathbf{\$22.33\text{ to }\$24.67}).$$

**Answer:** (a) $0.0170$; (b) $0.9037$; (c) between $\$22.34$ and $\$24.66$ (or $\$22.33$ and $\$24.67$ using $z = 1.65$).

✔ *Checker: Recomputed in Python; $z_1 = -1.4142, z_2 = 2.1213$.*

---

### Exercise 8.39
**Problem:** The mean SAT score for Division I student-athletes is 947 with a standard deviation of 205. If you select a random sample of 60 of these students, what is the probability the mean is below 900?

**Given:** $\mu = 947$, $\sigma = 205$, $n = 60$, $\bar{X} < 900$.

Compute $z$:
$$z = \frac{900 - 947}{205 / \sqrt{60}} = \frac{-47}{26.46539} = \mathbf{-1.78}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.78$ is $0.4625$, so:
$$P(\bar{X} < 900) = 0.5000 - 0.4625 = \mathbf{0.0375}.$$

**Answer:** $z = -1.78$, so $P(\bar{X} < 900) = \mathbf{0.0375}$.

✔ *Checker: Matches Lind Appendix C ($z = -1.78$, $P = 0.0375$).*

---

### Exercise 8.40
**Problem:** Suppose we roll a fair die two times.
(a) How many different samples are there?
(b) List each of the possible samples and compute the mean.
(c) On a chart similar to Chart 8–1, compare the distribution of sample means with the distribution of the population.
(d) Compute the mean and the standard deviation of each distribution and compare them.

**Given:** Fair six-sided die with population outcomes $X \in \{1, 2, 3, 4, 5, 6\}$ ($N = 6$, equally likely), rolled $n = 2$ times (sampling with replacement).

**(a)** Since each roll has 6 outcomes and rolls are independent (with replacement), there are:
$$6 \times 6 = \mathbf{36}\text{ different samples}.$$

**(b)** The 36 ordered pairs $(X_1, X_2)$ and their sample means $\bar{X} = (X_1 + X_2)/2$:

| $\bar{X}$ | Samples $(X_1, X_2)$ | Frequency | Probability |
|---|---|---|---|
| **1.0** | (1,1) | 1 | $1/36 \approx 0.0278$ |
| **1.5** | (1,2), (2,1) | 2 | $2/36 \approx 0.0556$ |
| **2.0** | (1,3), (2,2), (3,1) | 3 | $3/36 \approx 0.0833$ |
| **2.5** | (1,4), (2,3), (3,2), (4,1) | 4 | $4/36 \approx 0.1111$ |
| **3.0** | (1,5), (2,4), (3,3), (4,2), (5,1) | 5 | $5/36 \approx 0.1389$ |
| **3.5** | (1,6), (2,5), (3,4), (4,3), (5,2), (6,1) | 6 | $6/36 \approx 0.1667$ |
| **4.0** | (2,6), (3,5), (4,4), (5,3), (6,2) | 5 | $5/36 \approx 0.1389$ |
| **4.5** | (3,6), (4,5), (5,4), (6,3) | 4 | $4/36 \approx 0.1111$ |
| **5.0** | (4,6), (5,5), (6,4) | 3 | $3/36 \approx 0.0833$ |
| **5.5** | (5,6), (6,5) | 2 | $2/36 \approx 0.0556$ |
| **6.0** | (6,6) | 1 | $1/36 \approx 0.0278$ |
| **Total** | | **36** | **1.0000** |

**(c)** The population distribution is **uniform (flat)** over $1, 2, 3, 4, 5, 6$ ($P = 1/6$ each), whereas the distribution of sample means is **symmetric and triangular (mound-shaped)**, peaking at $\bar{X} = 3.5$ ($P = 6/36$).

**(d)** Mean and standard deviation of each distribution:
- **Population:** $\mu = \frac{1+2+3+4+5+6}{6} = \mathbf{3.50}$, $\sigma = \sqrt{\frac{17.5}{6}} = \sqrt{2.9167} \approx \mathbf{1.7078}$.
- **Sample means ($n=2$):** $\mu_{\bar{X}} = \mathbf{3.50}$, $\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{2}} = \sqrt{\frac{35}{24}} = \sqrt{1.4583} \approx \mathbf{1.2076}$.
The means are identical ($3.50$), while the standard error of the sample mean ($1.2076$) is smaller than the population standard deviation ($1.7078$) by a factor of $1/\sqrt{2}$.

**Answer:** (a) 36 samples; (b)–(c) triangular distribution on $1.0, 1.5, \dots, 6.0$ with frequencies $1, 2, 3, 4, 5, 6, 5, 4, 3, 2, 1$ vs. uniform population; (d) $\mu = \mu_{\bar{X}} = 3.50$, $\sigma = 1.7078$, and $\sigma_{\bar{X}} = 1.2076$.

✔ *Checker: Recomputed in Python; $\sigma^2 = 35/12 \approx 2.9167$, $\sigma_{\bar{X}}^2 = 35/24 \approx 1.4583$.*

---

### Exercise 8.41
**Problem:** Following is a list of the 50 states with the numbers 0 through 49 assigned to them.
(a) You wish to select a sample of eight from this list. The selected random numbers are 45, 15, 81, 09, 39, 43, 90, 26, 06, 45, 01, and 42. Which states are included in the sample?
(b) You wish to use a systematic sample of every sixth item and the digit 02 is chosen as the starting point. Which states are included?

| Number | State | Number | State |
|---|---|---|---|
| 0 | Alabama | 25 | Montana |
| 1 | Alaska | 26 | Nebraska |
| 2 | Arizona | 27 | Nevada |
| 3 | Arkansas | 28 | New Hampshire |
| 4 | California | 29 | New Jersey |
| 5 | Colorado | 30 | New Mexico |
| 6 | Connecticut | 31 | New York |
| 7 | Delaware | 32 | North Carolina |
| 8 | Florida | 33 | North Dakota |
| 9 | Georgia | 34 | Ohio |
| 10 | Hawaii | 35 | Oklahoma |
| 11 | Idaho | 36 | Oregon |
| 12 | Illinois | 37 | Pennsylvania |
| 13 | Indiana | 38 | Rhode Island |
| 14 | Iowa | 39 | South Carolina |
| 15 | Kansas | 40 | South Dakota |
| 16 | Kentucky | 41 | Tennessee |
| 17 | Louisiana | 42 | Texas |
| 18 | Maine | 43 | Utah |
| 19 | Maryland | 44 | Vermont |
| 20 | Massachusetts | 45 | Virginia |
| 21 | Michigan | 46 | Washington |
| 22 | Minnesota | 47 | West Virginia |
| 23 | Mississippi | 48 | Wisconsin |
| 24 | Missouri | 49 | Wyoming |

**Given:** $N = 50$ states numbered `0` (`00`) through `49`.

**(a)** From `45, 15, 81, 09, 39, 43, 90, 26, 06, 45, 01, 42`, skip `81` and `90` (out of range `00`–`49`) and skip the duplicate `45`. The first 8 unique valid numbers are `45, 15, 09, 39, 43, 26, 06, 01`:
- **45:** Virginia
- **15:** Kansas
- **09:** Georgia
- **39:** South Carolina
- **43:** Utah
- **26:** Nebraska
- **06:** Connecticut
- **01:** Alaska

**(b)** Starting at `02` and selecting every 6th state ($02, 08, 14, 20, 26, 32, 38, 44$):
- **02:** Arizona
- **08:** Florida
- **14:** Iowa
- **20:** Massachusetts
- **26:** Nebraska
- **32:** North Carolina
- **38:** Rhode Island
- **44:** Vermont

**Answer:** (a) Virginia (45), Kansas (15), Georgia (09), South Carolina (39), Utah (43), Nebraska (26), Connecticut (06), and Alaska (01); (b) Arizona (02), Florida (08), Iowa (14), Massachusetts (20), Nebraska (26), North Carolina (32), Rhode Island (38), and Vermont (44).

✔ *Checker: Matches Lind Appendix C exactly.*

---

### Exercise 8.42
**Problem:** Human Resource Consulting (HRC) surveyed a random sample of 60 Twin Cities construction companies to find information on the costs of their health care plans. One of the items being tracked is the annual deductible that employees must pay. The Minnesota Department of Labor reports that historically the mean deductible amount per employee is $502 with a standard deviation of $100.
(a) Compute the standard error of the sample mean for HRC.
(b) What is the chance HRC finds a sample mean between $477 and $527?
(c) Calculate the likelihood that the sample mean is between $492 and $512.
(d) What is the probability the sample mean is greater than $550?

**Given:** $\mu = \$502$, $\sigma = \$100$, $n = 60$.

**(a)** Standard error of the sample mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{100}{\sqrt{60}} \approx \mathbf{\$12.9099}\text{ (or }\$12.91\text{)}.$$

**(b)** For $\bar{X} = 477$ and $\bar{X} = 527$:
$$z = \frac{\pm 25}{12.9099} = \mathbf{\pm 1.94}.$$
📘 From Appendix B.1, the area between $0$ and $z = 1.94$ is $0.4738$, so:
$$P(477 < \bar{X} < 527) = 0.4738 + 0.4738 = \mathbf{0.9476}\text{ (exact }0.94722\text{)}.$$

**(c)** For $\bar{X} = 492$ and $\bar{X} = 512$:
$$z = \frac{\pm 10}{12.9099} = \mathbf{\pm 0.77}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.77$ is $0.2794$, so:
$$P(492 < \bar{X} < 512) = 0.2794 + 0.2794 = \mathbf{0.5588}\text{ (exact }0.56143\text{)}.$$

**(d)** For $\bar{X} > 550$:
$$z = \frac{550 - 502}{12.9099} = \frac{48}{12.9099} = \mathbf{3.72}.$$
📘 From Appendix B.1, for $z = 3.72$, the upper-tail probability is:
$$P(\bar{X} > 550) \approx \mathbf{0.0001}\text{ (exact }0.00010\text{)}.$$

**Answer:** (a) $\sigma_{\bar{X}} = \$12.91$; (b) $0.9476$; (c) $0.5588$; (d) $0.0001$.

✔ *Checker: Recomputed in Python; $\sigma_{\bar{X}} = 12.9099$, $z = \pm 1.9365, \pm 0.7746, 3.7181$.*

---

### Exercise 8.43
**Problem:** Over the past decade, the mean number of members of the Information Systems Security Association who have experienced a denial-of-service attack each year is 510, with a standard deviation of 14.28 attacks. Suppose nothing in this environment changes.
(a) What is the likelihood this group will suffer an average of more than 600 attacks in the next 10 years?
(b) Compute the probability the mean number of attacks over the next 10 years is between 500 and 600.
(c) What is the possibility they will experience an average of less than 500 attacks over the next 10 years?

**Given:** $\mu = 510$ attacks, $\sigma = 14.28$ attacks, $n = 10$ years.

Standard error:
$$\sigma_{\bar{X}} = \frac{14.28}{\sqrt{10}} \approx 4.51573.$$

**(a)** For $\bar{X} > 600$:
$$z = \frac{600 - 510}{14.28 / \sqrt{10}} = \frac{90}{4.51573} = \mathbf{19.93}.$$
Thus, $P(\bar{X} > 600) = \mathbf{0.0000}$ (virtually never).

**(b)** For $\bar{X} = 500$:
$$z = \frac{500 - 510}{14.28 / \sqrt{10}} = \frac{-10}{4.51573} = \mathbf{-2.21}.$$
📘 From Appendix B.1, the area between $0$ and $z = -2.21$ is $0.4864$, and the area between $0$ and $z = 19.93$ is $0.5000$, so:
$$P(500 < \bar{X} < 600) = 0.4864 + 0.5000 = \mathbf{0.9864}.$$

**(c)** For $\bar{X} < 500$ ($z < -2.21$):
$$P(\bar{X} < 500) = 0.5000 - 0.4864 = \mathbf{0.0136}.$$

**Answer:** (a) $0.0000$ (virtually never); (b) $0.9864$; (c) $0.0136$.

✔ *Checker: Matches Lind Appendix C ($z = 19.9, P = 0.00$; $z = -2.21, P = 0.9864$; $P = 0.0136$).*

---

### Exercise 8.44
**Problem:** The Oil Price Information Center of greater Houston reports the mean price per gallon of regular gasoline is $3.00 with a population standard deviation of $0.18. Assume a random sample of 40 gasoline stations is selected and their mean cost for regular gasoline is computed.
(a) What is the standard error of the mean in this experiment?
(b) What is the probability that the sample mean is between $2.98 and $3.02?
(c) What is the probability that the difference between the sample mean and the population mean is less than 0.01?
(d) What is the likelihood the sample mean is greater than $3.08?

**Given:** $\mu = \$3.00$, $\sigma = \$0.18$, $n = 40$.

**(a)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{0.18}{\sqrt{40}} \approx \mathbf{\$0.02846}\text{ (or }\$0.0285\text{)}.$$

**(b)** For $\bar{X} = 2.98$ and $\bar{X} = 3.02$:
$$z = \frac{\pm 0.02}{0.02846} = \mathbf{\pm 0.70}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.70$ is $0.2580$, so:
$$P(2.98 < \bar{X} < 3.02) = 0.2580 + 0.2580 = \mathbf{0.5160}\text{ (exact }0.51746\text{)}.$$

**(c)** Difference $|\bar{X} - \mu| < 0.01$:
$$z = \frac{\pm 0.01}{0.02846} = \mathbf{\pm 0.35}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.35$ is $0.1368$, so:
$$P(|\bar{X} - \mu| < 0.01) = 0.1368 + 0.1368 = \mathbf{0.2736}\text{ (exact }0.27472\text{)}.$$

**(d)** For $\bar{X} > 3.08$:
$$z = \frac{3.08 - 3.00}{0.02846} = \frac{0.08}{0.02846} = \mathbf{2.81}.$$
📘 From Appendix B.1, the area between $0$ and $z = 2.81$ is $0.4975$, so:
$$P(\bar{X} > 3.08) = 0.5000 - 0.4975 = \mathbf{0.0025}\text{ (exact }0.00247\text{)}.$$

**Answer:** (a) $\sigma_{\bar{X}} = \$0.0285$; (b) $0.5160$; (c) $0.2736$; (d) $0.0025$.

✔ *Checker: Recomputed in Python; $\sigma_{\bar{X}} = 0.02846$, $z = \pm 0.7027, \pm 0.3514, 2.8109$.*

---

### Exercise 8.45
**Problem:** Nike's annual report says that the average American buys 6.5 pairs of sports shoes per year. Suppose the population standard deviation is 2.1 and that a sample of 81 customers will be examined next year.
(a) What is the standard error of the mean in this experiment?
(b) What is the probability that the sample mean is between 6 and 7 pairs of sports shoes?
(c) What is the probability that the difference between the sample mean and the population mean is less than 0.25 pairs?
(d) What is the likelihood the sample mean is greater than 7 pairs?

**Given:** $\mu = 6.5$ pairs, $\sigma = 2.1$ pairs, $n = 81$.

**(a)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{2.1}{\sqrt{81}} = \frac{2.1}{9} = \mathbf{0.2333\text{ pairs}}\text{ (or }0.23\text{)}.$$

**(b)** For $\bar{X} = 6.0$ and $\bar{X} = 7.0$:
$$z = \frac{\pm 0.5}{2.1 / 9} = \frac{\pm 0.5}{0.2333} = \mathbf{\pm 2.14}.$$
📘 From Appendix B.1, the area between $0$ and $z = 2.14$ is $0.4838$, so:
$$P(6 < \bar{X} < 7) = 0.4838 + 0.4838 = \mathbf{0.9676}.$$

**(c)** For $|\bar{X} - \mu| < 0.25$ ($6.25 < \bar{X} < 6.75$):
$$z = \frac{\pm 0.25}{2.1 / 9} = \mathbf{\pm 1.07}.$$
📘 From Appendix B.1, the area between $0$ and $z = 1.07$ is $0.3577$, so:
$$P(|\bar{X} - \mu| < 0.25) = 0.3577 + 0.3577 = \mathbf{0.7154}.$$

**(d)** For $\bar{X} > 7.0$ ($z > 2.14$):
$$P(\bar{X} > 7) = 0.5000 - 0.4838 = \mathbf{0.0162}.$$

**Answer:** (a) $\sigma_{\bar{X}} = 0.2333$ (or $0.23$); (b) $0.9676$; (c) $0.7154$; (d) $0.0162$.

✔ *Checker: Matches Lind Appendix C ($0.23$, $0.9676$, $0.7154$, $0.0162$).*

---

## Lind — Chapter 8: Data Set Exercises

### Exercise 8.46
**Problem:** Refer to the Real Estate data, which report information on the homes sold in the Goodyear, Arizona, area last year. Use statistical software to compute the mean and the standard deviation of the selling prices. Assume this to be the population. Select a sample of 10 homes. Compute the mean and the standard deviation of the sample. Determine the likelihood of a sample mean this large or larger from the population.

**Given:** Goodyear, Arizona, Real Estate Data Set (Appendix A.1, $N = 105$ homes).

**Step 1 — Population parameters ($N = 105$):**
$$\mu = \frac{\sum X}{105} = \frac{23,215.8}{105} = \mathbf{\$221.1029\text{ thousand}}, \qquad \sigma = \mathbf{\$46.8806\text{ thousand}}\text{ (or }s = \$47.1054\text{ thousand)}.$$

**Step 2 — Sample of $n = 10$ homes:**
Answers will vary by random sample. Using the first 10 homes in Appendix A.1 (`263.1, 182.4, 242.1, 213.6, 139.9, 245.4, 327.2, 271.8, 221.1, 266.6`):
$$\bar{X} = \mathbf{\$237.32\text{ thousand}}, \qquad s_{\text{sample}} = \mathbf{\$51.84\text{ thousand}}.$$

**Step 3 — Probability of a sample mean this large or larger:**
With $\sigma_{\bar{X}} = \frac{47.1054}{\sqrt{10}} = 14.8960$:
$$z = \frac{237.32 - 221.1029}{14.8960} = \mathbf{1.09} \implies P(\bar{X} \ge 237.32) = 0.5000 - 0.3621 = \mathbf{0.1379}.$$

**Answer:** Population mean $\mu = \$221.10$ thousand, standard deviation $\$47.11$ thousand (or $\sigma = \$46.88$ thousand); for an illustrative sample of 10 homes, $\bar{X} = \$237.32$ thousand, $s = \$51.84$ thousand, $z = 1.09$, and $P(\bar{X} \ge 237.32) = 0.1379$ (sample results vary).

✔ *Checker: Verified from Appendix A.1 dataset ($N = 105$, $\sum X = 23,215.8$).*

---

### Exercise 8.47
**Problem:** Refer to the Baseball 2009 data, which report information on the 30 Major League Baseball teams for the 2009 season. Over the last decade, the mean attendance per team followed a normal distribution with a mean of 2.25 million per team and a standard deviation of 0.70 million. Use statistical software to compute the mean attendance per team for the 2009 season. Determine the likelihood of a sample mean this large or larger from the population.

**Given:** Baseball 2009 Data Set (Appendix A.2, $n = 30$ teams), historical normal distribution with $\mu = 2.25$ million and $\sigma = 0.70$ million.

**Step 1 — 2009 sample mean attendance ($n = 30$):**
Summing the 2009 attendance values across all 30 MLB teams in Appendix A.2 gives $\sum X = 73.43$ million:
$$\bar{X} = \frac{73.43}{30} = \mathbf{2.4477\text{ million}}\text{ (or }2.448\text{ million)}.$$

**Step 2 — Standard error and $z$-statistic:**
$$\sigma_{\bar{X}} = \frac{0.70}{\sqrt{30}} \approx 0.12780\text{ million}, \qquad z = \frac{2.448 - 2.25}{0.70 / \sqrt{30}} = \frac{0.198}{0.12780} = \mathbf{1.55}.$$
📘 From Appendix B.1, the area between $0$ and $z = 1.55$ is $0.4394$, so:
$$P(\bar{X} \ge 2.448) = 0.5000 - 0.4394 = \mathbf{0.0606}.$$

**Answer:** Mean 2009 attendance $\bar{X} = 2.448$ million, $z = 1.55$, and $P(\bar{X} \ge 2.448) = \mathbf{0.0606}$.

✔ *Checker: Matches Lind Appendix C ($\bar{X} = 2.448$ million, $z = 1.55$, $P = 0.0606$).*

---

### Exercise 8.48
**Problem:** Refer to the Buena School District bus data. Information provided by manufacturers of school buses suggests the mean maintenance cost per month is $455 per bus. Use statistical software to find the mean and the standard deviation for the Buena buses. Does the Buena data seem to be in line with that reported by the manufacturer? Specifically, what is the probability of the sample mean being less than Buena's, given the manufacturer's data?

**Given:** Buena School District Bus Data Set (Appendix A.3, $n = 80$ buses), manufacturer's mean $\mu = \$455$.

**Step 1 — Sample statistics from Appendix A.3 ($n = 80$):**
$$\bar{X} = \frac{\$36,023}{80} = \mathbf{\$450.29}, \qquad s = \mathbf{\$53.69}.$$

**Step 2 — Standard error and $z$-statistic (using $s = 53.69$ to estimate $\sigma$ since $n = 80$ is large):**
$$\sigma_{\bar{X}} \approx \frac{53.6860}{\sqrt{80}} = \$6.0023, \qquad z = \frac{450.2875 - 455.00}{6.0023} = \mathbf{-0.79}\text{ (exact }-0.7851\text{)}.$$
📘 From Appendix B.1, the area between $0$ and $z = -0.79$ is $0.2852$ (or $0.2823$ for $z = -0.78$), so:
$$P(\bar{X} < 450.29) = 0.5000 - 0.2852 = \mathbf{0.2148}\text{ (exact }0.2162\text{)}.$$
Because a sample mean this low or lower occurs over $21\%$ of the time by chance when $\mu = \$455$, **yes, the Buena data are in line with the manufacturer's reported mean of $\$455$**.

**Answer:** $\bar{X} = \$450.29$, $s = \$53.69$, $z = -0.79$, and $P(\bar{X} < \$450.29) = \mathbf{0.2148}$ (exact $0.2162$); yes, the Buena maintenance costs are consistent with the manufacturer's $\$455$ figure.

✔ *Checker: Verified from Appendix A.3 ($n = 80$, $\bar{X} = 450.2875$, $s = 53.6860$, $z = -0.7851$).*

---

# Lind — Chapter 9: Estimation and Confidence Intervals

**Scope:** Every exercise in Chapter 9 of Douglas A. Lind, William G. Marchal, and Samuel A. Wathen, *Statistical Techniques in Business & Economics* (15th ed.): Section Exercises 9.1–9.8 (§9.3, pp. 305–306), 9.9–9.14 (§9.3 $\sigma$ unknown, pp. 312–313), 9.15–9.18 (§9.4, p. 316), 9.19–9.26 (§9.5, p. 320), 9.27–9.30 (§9.6, p. 322), Chapter Exercises 9.31–9.68 (pp. 323–327), Data Set Exercises 9.69–9.71 (pp. 327–328), and Review of Chapters 8–9 Problems & Practice Test (9.72–9.86, pp. 331–332).

**How tables were used:** Normal critical values $z$ come from Appendix B.1 ($z_{0.90} = 1.65$ or $1.645$, $z_{0.95} = 1.96$, $z_{0.98} = 2.33$, $z_{0.99} = 2.58$), and Student's $t$ critical values come from Appendix B.2 with $df = n - 1$ (to 3 decimal places). Both Lind's table-rounded values and exact `scipy.stats` values are given.

**Conventions (Lind §§9.2–9.6):**
- Confidence interval for $\mu$ ($\sigma$ known): $\bar{X} \pm z \frac{\sigma}{\sqrt{n}}$.
- Confidence interval for $\mu$ ($\sigma$ unknown): $\bar{X} \pm t_{df,\,\alpha/2} \frac{s}{\sqrt{n}}$ with $df = n - 1$.
- Confidence interval for a population proportion: $p \pm z \sqrt{\frac{p(1-p)}{n}}$ where $p = X/n$.
- Sample size for $\mu$: $n = \left(\frac{z\sigma}{E}\right)^2$ (always rounded up to the next integer).
- Sample size for $\pi$: $n = \pi(1-\pi)\left(\frac{z}{E}\right)^2$ (use $\pi = 0.50$ if no prior estimate is available).
- Finite-population correction factor (FPC): $\sqrt{\frac{N - n}{N - 1}}$.

---

## Lind — Chapter 9, Section 9.3: Confidence Intervals for a Population Mean ($\sigma$ Known)

### Exercise 9.1
**Problem:** A sample of 49 observations is taken from a normal population with a standard deviation of 10. The sample mean is 55. Determine the 99 percent confidence interval for the population mean.

**Given:** $n = 49$, $\sigma = 10$, $\bar{X} = 55$, $99\%$ confidence level.

📘 From Appendix B.1, for a $99\%$ confidence level ($0.4950$ in each half), $z = 2.58$ (exact $2.5758$):
$$\bar{X} \pm z \frac{\sigma}{\sqrt{n}} = 55 \pm 2.58 \left(\frac{10}{\sqrt{49}}\right) = 55 \pm 2.58 \left(\frac{10}{7}\right) = 55 \pm 3.686.$$
Endpoints: **$51.314$ and $58.686$** (or $51.31$ and $58.69$).

**Answer:** **$51.314$ to $58.686$** (found by $55 \pm 2.58(10/\sqrt{49})$).

✔ *Checker: Matches Lind Appendix C ($51.314$ and $58.686$).*

---

### Exercise 9.2
**Problem:** A sample of 81 observations is taken from a normal population with a standard deviation of 5. The sample mean is 40. Determine the 95 percent confidence interval for the population mean.

**Given:** $n = 81$, $\sigma = 5$, $\bar{X} = 40$, $95\%$ confidence level.

📘 From Appendix B.1, for a $95\%$ confidence level, $z = 1.96$:
$$\bar{X} \pm z \frac{\sigma}{\sqrt{n}} = 40 \pm 1.96 \left(\frac{5}{\sqrt{81}}\right) = 40 \pm 1.96 \left(\frac{5}{9}\right) = 40 \pm 1.089.$$
Endpoints: **$38.911$ and $41.089$** (or $38.91$ and $41.09$).

**Answer:** **$38.911$ to $41.089$** (or **$38.91$ to $41.09$**).

✔ *Checker: Recomputed in Python; $1.96 \times 5 / 9 = 1.0889$.*

---

### Exercise 9.3
**Problem:** A sample of 250 observations is selected from a normal population for which the population standard deviation is known to be 25. The sample mean is 20.
(a) Determine the standard error of the mean.
(b) Explain why we can use formula (9–1) to determine the 95 percent confidence interval.
(c) Determine the 95 percent confidence interval for the population mean.

**Given:** $n = 250$, $\sigma = 25$, $\bar{X} = 20$, $95\%$ confidence level.

**(a)** Standard error of the mean:
$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}} = \frac{25}{\sqrt{250}} \approx \mathbf{1.5811}\text{ (or }1.581\text{)}.$$

**(b)** We can use formula (9–1), $\bar{X} \pm z(\sigma / \sqrt{n})$, because **the population is normally distributed and the population standard deviation ($\sigma = 25$) is known**.

**(c)** With $z = 1.96$:
$$20 \pm 1.96 \left(\frac{25}{\sqrt{250}}\right) = 20 \pm 1.96(1.58114) = 20 \pm 3.099.$$
Endpoints: **$16.901$ and $23.099$** (or $16.90$ and $23.10$).

**Answer:** (a) $\sigma_{\bar{X}} = 1.581$; (b) the population is normally distributed and $\sigma$ is known; (c) **$16.901$ to $23.099$**.

✔ *Checker: Matches Lind Appendix C ($1.581$, $16.901$ and $23.099$).*

---

### Exercise 9.4
**Problem:** Suppose you know $\sigma$ and you want an 85 percent confidence level. What value would you use to multiply the standard error of the mean by?

**Given:** Known $\sigma$, $85\%$ confidence level.

An $85\%$ confidence interval places $0.8500 / 2 = 0.4250$ of the area on each side of the mean $0$.
📘 In Appendix B.1, the area $0.4251$ corresponds to **$z = 1.44$** (exact $z_{0.075} = 1.4395$).

**Answer:** **$z = 1.44$** (exact $1.4395$).

✔ *Checker: `scipy.stats.norm.ppf(0.925)` gives $1.43953$.*

---

### Exercise 9.5
**Problem:** A research firm conducted a survey to determine the mean amount steady smokers spend on cigarettes during a week. They found the distribution of amounts spent per week followed the normal distribution with a population standard deviation of $5. A sample of 49 steady smokers revealed that $\bar{X} = \$20$.
(a) What is the point estimate of the population mean? Explain what it indicates.
(b) Using the 95 percent level of confidence, determine the confidence interval for $\mu$. Explain what it indicates.

**Given:** Normal population with $\sigma = \$5$, $n = 49$, $\bar{X} = \$20$, $95\%$ confidence level.

**(a)** The point estimate of the population mean is **$\$20$** (the sample mean $\bar{X}$). It is our best single-value estimate of the unknown population mean weekly expenditure on cigarettes.

**(b)** With $z = 1.96$:
$$\$20 \pm 1.96 \left(\frac{\$5}{\sqrt{49}}\right) = \$20 \pm 1.96 \left(\frac{\$5}{7}\right) = \$20 \pm \$1.40.$$
The $95\%$ confidence interval is **$\$18.60$ to $\$21.40$**. About $95\%$ of all confidence intervals constructed in this manner from samples of size 49 will contain the true population mean $\mu$.

**Answer:** (a) $\$20$, the best estimate of the population mean; (b) **$\$18.60$ to $\$21.40$** (about 95% of similarly constructed intervals will include $\mu$).

✔ *Checker: Matches Lind Appendix C ($\$20$; $\$18.60$ and $\$21.40$).*

---

### Exercise 9.6
**Problem:** Refer to the previous exercise. Suppose that 64 smokers (instead of 49) were sampled. Assume the sample mean remained the same.
(a) What is the 95 percent confidence interval estimate of $\mu$?
(b) Explain why this confidence interval is narrower than the one determined in the previous exercise.

**Given:** $\sigma = \$5$, $n = 64$, $\bar{X} = \$20$, $95\%$ confidence level ($z = 1.96$).

**(a)** Confidence interval:
$$\$20 \pm 1.96 \left(\frac{\$5}{\sqrt{64}}\right) = \$20 \pm 1.96 \left(\frac{\$5}{8}\right) = \$20 \pm \$1.225 = \mathbf{\$18.78\text{ to }\$21.23}\text{ (exact }\$18.775\text{ to }\$21.225\text{)}.$$

**(b)** The confidence interval is narrower because **the sample size increased from $49$ to $64$, which reduced the standard error of the mean** from $\$5/7 \approx \$0.714$ to $\$5/8 = \$0.625$.

**Answer:** (a) **$\$18.775$ to $\$21.225$** (or **$\$18.78$ to $\$21.23$**); (b) increasing the sample size $n$ from 49 to 64 decreases the standard error $\sigma / \sqrt{n}$.

✔ *Checker: Recomputed in Python; $1.96 \times 5 / 8 = 1.225$.*

---

### Exercise 9.7
**Problem:** Bob Nale is the owner of Nale's Quick Fill. Bob would like to estimate the mean number of gallons of gasoline sold to his customers. Assume the number of gallons sold follows the normal distribution with a population standard deviation of 2.30 gallons. From his records, he selects a random sample of 60 sales and finds the mean number of gallons sold is 8.60.
(a) What is the point estimate of the population mean?
(b) Develop a 99 percent confidence interval for the population mean.
(c) Interpret the meaning of part (b).

**Given:** $\sigma = 2.30$ gallons, $n = 60$, $\bar{X} = 8.60$ gallons, $99\%$ confidence level.

**(a)** The point estimate of the population mean is **$8.60$ gallons**.

**(b)** With $z = 2.58$ for $99\%$ confidence:
$$8.60 \pm 2.58 \left(\frac{2.30}{\sqrt{60}}\right) = 8.60 \pm 2.58(0.29693) = 8.60 \pm 0.766 = \mathbf{7.83\text{ to }9.37\text{ gallons}}.$$

**(c)** If 100 such $99\%$ confidence intervals were constructed from repeated random samples of 60 sales, the population mean $\mu$ would be included in about 99 of the intervals.

**Answer:** (a) $8.60$ gallons; (b) **$7.83$ to $9.37$ gallons**; (c) about 99 out of 100 similarly constructed intervals will contain the true population mean.

✔ *Checker: Matches Lind Appendix C ($8.60$ gallons; $7.83$ and $9.37$).*

---

### Exercise 9.8
**Problem:** Dr. Patton is a professor of English. Recently she counted the number of misspelled words in a group of student essays. She noted the distribution of misspelled words per essay followed the normal distribution with a population standard deviation of 2.44 words per essay. For her 10 A.M. section of 40 students, the mean number of misspelled words was 6.05. Construct a 95 percent confidence interval for the mean number of misspelled words in the population of student essays.

**Given:** $\sigma = 2.44$, $n = 40$, $\bar{X} = 6.05$, $95\%$ confidence level ($z = 1.96$).

Compute the $95\%$ confidence interval:
$$6.05 \pm 1.96 \left(\frac{2.44}{\sqrt{40}}\right) = 6.05 \pm 1.96(0.38580) = 6.05 \pm 0.756 = \mathbf{5.29\text{ to }6.81\text{ words}}\text{ (exact }5.294\text{ to }6.806\text{)}.$$

**Answer:** **$5.29$ to $6.81$ words** ($5.294$ to $6.806$).

✔ *Checker: Recomputed in Python; $1.96 \times 2.44 / \sqrt{40} = 0.75617$.*

---

## Lind — Chapter 9, Section 9.3: Confidence Intervals for a Population Mean ($\sigma$ Unknown)

### Exercise 9.9
**Problem:** Use Appendix B.2 to locate the value of $t$ under the following conditions.
(a) The sample size is 12 and the level of confidence is 95 percent.
(b) The sample size is 20 and the level of confidence is 90 percent.
(c) The sample size is 8 and the level of confidence is 99 percent.

📘 Looking up $df = n - 1$ in Appendix B.2 (Student's $t$ Distribution):
- **(a)** $n = 12 \implies df = 11$, $95\%$ confidence: **$t = 2.201$**.
- **(b)** $n = 20 \implies df = 19$, $90\%$ confidence: **$t = 1.729$**.
- **(c)** $n = 8 \implies df = 7$, $99\%$ confidence: **$t = 3.499$**.

**Answer:** (a) $2.201$; (b) $1.729$; (c) $3.499$.

✔ *Checker: Matches Lind Appendix C ($2.201, 1.729, 3.499$).*

---

### Exercise 9.10
**Problem:** Use Appendix B.2 to locate the value of $t$ under the following conditions.
(a) The sample size is 15 and the level of confidence is 95 percent.
(b) The sample size is 24 and the level of confidence is 98 percent.
(c) The sample size is 12 and the level of confidence is 90 percent.

📘 Looking up $df = n - 1$ in Appendix B.2:
- **(a)** $n = 15 \implies df = 14$, $95\%$ confidence: **$t = 2.145$**.
- **(b)** $n = 24 \implies df = 23$, $98\%$ confidence: **$t = 2.500$**.
- **(c)** $n = 12 \implies df = 11$, $90\%$ confidence: **$t = 1.796$**.

**Answer:** (a) $2.145$; (b) $2.500$; (c) $1.796$.

✔ *Checker: Verified via `scipy.stats.t.ppf` ($2.14479, 2.49987, 1.79588$).*

---

### Exercise 9.11
**Problem:** The owner of Britten's Egg Farm wants to estimate the mean number of eggs laid per chicken. A sample of 20 chickens shows they laid an average of 20 eggs per month with a standard deviation of 2 eggs per month.
(a) What is the value of the population mean? What is the best estimate of this value?
(b) Explain why we need to use the $t$ distribution. What assumption do you need to make?
(c) For a 95 percent confidence interval, what is the value of $t$?
(d) Develop the 95 percent confidence interval for the population mean.
(e) Would it be reasonable to conclude that the population mean is 21 eggs? What about 25 eggs?

**Given:** $n = 20$, $\bar{X} = 20$, $s = 2$, $95\%$ confidence level.

**(a)** The population mean $\mu$ is **unknown**, and the best estimate of it is the sample mean, **$20$ eggs**.

**(b)** We use the $t$ distribution because **the population standard deviation $\sigma$ is unknown** and estimated by $s = 2$. We must assume that **the population of eggs laid per chicken follows a normal distribution**.

**(c)** With $df = n - 1 = 19$ and $95\%$ confidence, Appendix B.2 gives **$t = 2.093$**.

**(d)** $95\%$ confidence interval:
$$20 \pm 2.093 \left(\frac{2}{\sqrt{20}}\right) = 20 \pm 2.093(0.44721) = 20 \pm 0.936 = \mathbf{19.06\text{ to }20.94\text{ eggs}}.$$

**(e)** **Neither $21$ nor $25$ eggs is reasonable**, because both values lie outside the $95\%$ confidence interval ($19.06$ to $20.94$).

**Answer:** (a) Unknown; best estimate is 20; (b) $\sigma$ is unknown, and we assume the population is normally distributed; (c) $t = 2.093$; (d) **$19.06$ to $20.94$ eggs**; (e) neither 21 nor 25 is reasonable because both lie outside $[19.06, 20.94]$.

✔ *Checker: Matches Lind Appendix C ($20$, $2.093$, $19.06$ and $20.94$, neither value is reasonable).*

---

### Exercise 9.12
**Problem:** The U.S. Dairy Industry wants to estimate the mean yearly milk consumption. A sample of 16 people reveals the mean yearly consumption to be 60 gallons with a standard deviation of 20 gallons.
(a) What is the value of the population mean? What is the best estimate of this value?
(b) Explain why we need to use the $t$ distribution. What assumption do you need to make?
(c) For a 90 percent confidence interval, what is the value of $t$?
(d) Develop the 90 percent confidence interval for the population mean.
(e) Would it be reasonable to conclude that the population mean is 63 gallons?

**Given:** $n = 16$, $\bar{X} = 60$ gallons, $s = 20$ gallons, $90\%$ confidence level.

**(a)** The population mean $\mu$ is **unknown**; the best estimate is the sample mean, **$60$ gallons**.

**(b)** We use the $t$ distribution because **the population standard deviation $\sigma$ is unknown**. We must assume that **the population of yearly milk consumption is normally distributed**.

**(c)** With $df = n - 1 = 15$ and $90\%$ confidence, Appendix B.2 gives **$t = 1.753$**.

**(d)** $90\%$ confidence interval:
$$60 \pm 1.753 \left(\frac{20}{\sqrt{16}}\right) = 60 \pm 1.753(5) = 60 \pm 8.765 = \mathbf{51.235\text{ to }68.765\text{ gallons}}\text{ (or }51.24\text{ to }68.77\text{)}.$$

**(e)** **Yes**, $63$ gallons is reasonable because $63$ falls inside the $90\%$ confidence interval ($51.24$ to $68.77$).

**Answer:** (a) Unknown; best estimate is 60 gallons; (b) $\sigma$ is unknown, and we assume a normal population; (c) $t = 1.753$; (d) **$51.235$ to $68.765$ gallons** ($51.24$ to $68.77$); (e) yes, 63 gallons is inside the interval.

✔ *Checker: Recomputed in Python; $1.753 \times 5 = 8.765$.*

---

### Exercise 9.13
**Problem:** Merrill Lynch Securities and Health Care Retirement Inc. are two large employers in downtown Toledo, Ohio. They are considering jointly offering child care for their employees. As a part of the feasibility study, they wish to estimate the mean weekly child-care cost of their employees. A sample of 10 employees who use child care reveals the following amounts spent last week.
$107 $92 $97 $95 $105 $101 $91 $99 $95 $104
Develop a 90 percent confidence interval for the population mean. Interpret the result.

**Given:** $n = 10$ weekly amounts: $107, 92, 97, 95, 105, 101, 91, 99, 95, 104$; $90\%$ confidence level.

**Step 1 — Sample mean and standard deviation:**
$$\bar{X} = \frac{986}{10} = \mathbf{\$98.60}, \qquad s = \sqrt{\frac{\sum (X - 98.6)^2}{9}} = \sqrt{\frac{276.40}{9}} = \sqrt{30.7111} \approx \mathbf{\$5.5418}.$$

**Step 2 — $90\%$ confidence interval ($df = 9$):**
📘 From Appendix B.2, for $df = 9$ at $90\%$ confidence, $t = 1.833$:
$$98.60 \pm 1.833 \left(\frac{5.5418}{\sqrt{10}}\right) = 98.60 \pm 1.833(1.75246) = 98.60 \pm 3.21 = \mathbf{\$95.39\text{ to }\$101.81}.$$
We are $90\%$ confident that the true population mean weekly child-care cost is between $\$95.39$ and $\$101.81$.

**Answer:** **$\$95.39$ to $\$101.81$** (where $\bar{X} = \$98.60$, $s = \$5.54$, $t = 1.833$).

✔ *Checker: Matches Lind Appendix C (Between 95.39 and 101.81, found by $98.6 \pm 1.833(5.54/\sqrt{10})$).*

---

### Exercise 9.14
**Problem:** The Greater Pittsburgh Area Chamber of Commerce wants to estimate the mean time workers who are employed in the downtown area spend getting to work. A sample of 15 workers reveals the following number of minutes spent traveling.
29 38 38 33 38 21 45 34 40 37 37 42 30 29 35
Develop a 98 percent confidence interval for the population mean. Interpret the result.

**Given:** $n = 15$ travel times: $29, 38, 38, 33, 38, 21, 45, 34, 40, 37, 37, 42, 30, 29, 35$; $98\%$ confidence level.

**Step 1 — Sample mean and standard deviation:**
$$\bar{X} = \frac{526}{15} \approx \mathbf{35.0667\text{ minutes}}, \qquad s = \sqrt{\frac{\sum (X - 35.0667)^2}{14}} = \sqrt{\frac{536.9333}{14}} = \sqrt{38.3524} \approx \mathbf{6.1929\text{ minutes}}.$$

**Step 2 — $98\%$ confidence interval ($df = 14$):**
📘 From Appendix B.2, for $df = 14$ at $98\%$ confidence, $t = 2.624$:
$$35.0667 \pm 2.624 \left(\frac{6.1929}{\sqrt{15}}\right) = 35.0667 \pm 2.624(1.59901) = 35.0667 \pm 4.1958 = \mathbf{30.87\text{ to }39.26\text{ minutes}}.$$
We are $98\%$ confident that the true mean commuting time for downtown Pittsburgh workers is between $30.87$ and $39.26$ minutes.

**Answer:** **$30.87$ to $39.26$ minutes** (where $\bar{X} = 35.07$, $s = 6.19$, $t = 2.624$).

✔ *Checker: Recomputed in Python; $\bar{X} = 35.0667, s = 6.1929, t = 2.62449$, CI $[30.870, 39.263]$.*

---

## Lind — Chapter 9, Section 9.4: A Confidence Interval for a Proportion

### Exercise 9.15
**Problem:** The owner of the West End Kwick Fill Gas Station wishes to determine the proportion of customers who use a credit card or debit card to pay at the pump. He surveys 100 customers and finds that 80 paid at the pump.
(a) Estimate the value of the population proportion.
(b) Develop a 95 percent confidence interval for the population proportion.
(c) Interpret your findings.

**Given:** $n = 100$, $X = 80$, $95\%$ confidence level ($z = 1.96$).

**(a)** Sample proportion:
$$p = \frac{X}{n} = \frac{80}{100} = \mathbf{0.80}.$$

**(b)** $95\%$ confidence interval:
$$p \pm z \sqrt{\frac{p(1-p)}{n}} = 0.80 \pm 1.96 \sqrt{\frac{0.80(0.20)}{100}} = 0.80 \pm 1.96(0.04) = 0.80 \pm 0.0784 = \mathbf{0.7216\text{ to }0.8784}\text{ (or }\mathbf{0.72\text{ to }0.88}\text{)}.$$

**(c)** We are $95\%$ confident that the true population proportion of customers who pay at the pump is between $72.16\%$ and $87.84\%$ (about $72\%$ to $88\%$).

**Answer:** (a) $p = 0.80$; (b) **$0.7216$ to $0.8784$** (or **$0.72$ to $0.88$**); (c) we are 95% confident that between 72% and 88% of customers pay at the pump.

✔ *Checker: Matches Lind Appendix C ($0.80$; between $0.72$ and $0.88$).*

---

### Exercise 9.16
**Problem:** Ms. Maria Wilson is considering running for mayor of the town of Bear Gulch, Montana. Before completing the petitions, she decides to conduct a survey of voters in Bear Gulch. A sample of 400 voters reveals that 300 would support her in the November election.
(a) Estimate the value of the population proportion.
(b) Develop a 99 percent confidence interval for the population proportion.
(c) Interpret your findings.

**Given:** $n = 400$, $X = 300$, $99\%$ confidence level ($z = 2.58$).

**(a)** Sample proportion:
$$p = \frac{300}{400} = \mathbf{0.75}.$$

**(b)** $99\%$ confidence interval:
$$0.75 \pm 2.58 \sqrt{\frac{0.75(0.25)}{400}} = 0.75 \pm 2.58(0.02165) = 0.75 \pm 0.0559 = \mathbf{0.6941\text{ to }0.8059}\text{ (or }\mathbf{0.694\text{ to }0.806}\text{)}.$$

**(c)** We are $99\%$ confident that between $69.4\%$ and $80.6\%$ of Bear Gulch voters support Ms. Wilson—well above the $50\%$ needed to win the election.

**Answer:** (a) $p = 0.75$; (b) **$0.694$ to $0.806$** ($0.6941$ to $0.8059$); (c) we are 99% confident that between 69.4% and 80.6% of voters support her.

✔ *Checker: Recomputed in Python; $2.58 \times \sqrt{0.1875/400} = 0.05586$.*

---

### Exercise 9.17
**Problem:** The Fox TV network is considering replacing one of its prime-time crime investigation shows with a new family-oriented comedy show. Before a final decision is made, network executives commission a sample of 400 viewers. After viewing the comedy, 250 indicated they would watch the new show and suggested it replace the crime investigation show.
(a) Estimate the value of the population proportion.
(b) Develop a 99 percent confidence interval for the population proportion.
(c) Interpret your findings.

**Given:** $n = 400$, $X = 250$, $99\%$ confidence level ($z = 2.58$).

**(a)** Sample proportion:
$$p = \frac{250}{400} = \mathbf{0.625}.$$

**(b)** $99\%$ confidence interval:
$$0.625 \pm 2.58 \sqrt{\frac{0.625(0.375)}{400}} = 0.625 \pm 2.58(0.024206) = 0.625 \pm 0.06245 = \mathbf{0.5625\text{ to }0.6875}\text{ (or }\mathbf{0.563\text{ to }0.687}\text{)}.$$

**(c)** We are $99\%$ confident that the true population proportion of viewers favoring the new comedy show is between $56.3\%$ and $68.7\%$ (a clear majority).

**Answer:** (a) $p = 0.625$; (b) **$0.563$ to $0.687$**; (c) we are 99% confident the population proportion is between 56.3% and 68.7%.

✔ *Checker: Matches Lind Appendix C ($0.625$; between $0.563$ and $0.687$).*

---

### Exercise 9.18
**Problem:** Schadek Silkscreen Printing Inc. purchases plastic cups on which to print logos for sporting events, proms, birthdays, and other special occasions. Zack Schadek, the owner, received a large shipment this morning. To ensure the quality of the shipment, he selected a random sample of 300 cups. He found 15 to be defective.
(a) What is the estimated proportion defective in the population?
(b) Develop a 95 percent confidence interval for the proportion defective.
(c) Zack has an agreement with his supplier that he is to return lots that are 10 percent or more defective. Should he return this lot? Explain your decision.

**Given:** $n = 300$, $X = 15$, $95\%$ confidence level ($z = 1.96$).

**(a)** Estimated proportion defective:
$$p = \frac{15}{300} = \mathbf{0.05}.$$

**(b)** $95\%$ confidence interval:
$$0.05 \pm 1.96 \sqrt{\frac{0.05(0.95)}{300}} = 0.05 \pm 1.96(0.012583) = 0.05 \pm 0.0247 = \mathbf{0.0253\text{ to }0.0747}.$$

**(c)** **No, he should not return the lot**, because the upper endpoint of the $95\%$ confidence interval ($0.0747$, or $7.47\%$) is well below $0.10$ ($10\%$).

**Answer:** (a) $p = 0.05$; (b) **$0.0253$ to $0.0747$**; (c) no, do not return the lot because the entire 95% confidence interval lies below 0.10 (10%).

✔ *Checker: Recomputed in Python; $0.05 \pm 0.02466 = [0.0253, 0.0747]$.*

---

## Lind — Chapter 9, Section 9.5: Choosing an Appropriate Sample Size

### Exercise 9.19
**Problem:** A population is estimated to have a standard deviation of 10. We want to estimate the population mean within 2, with a 95 percent level of confidence. How large a sample is required?

**Given:** $\sigma = 10$, $E = 2$, $95\%$ confidence ($z = 1.96$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 10}{2}\right)^2 = (9.8)^2 = 96.04 \implies \mathbf{n = 97}\text{ (rounded up)}.$$

**Answer:** **$n = 97$** ($96.04$ rounded up).

✔ *Checker: Matches Lind Appendix C (listed at item 23 due to Appendix C shift: $97$, found by $(1.96 \times 10/2)^2 = 96.04$).*

---

### Exercise 9.20
**Problem:** We want to estimate the population mean within 5, with a 99 percent level of confidence. The population standard deviation is estimated to be 15. How large a sample is required?

**Given:** $E = 5$, $\sigma = 15$, $99\%$ confidence ($z = 2.58$, or exact $2.5758$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{2.58 \times 15}{5}\right)^2 = (7.74)^2 = 59.9076 \implies \mathbf{n = 60}\text{ (rounded up)}.$$

**Answer:** **$n = 60$** ($59.91$ rounded up).

✔ *Checker: Both $z = 2.58$ ($59.91$) and exact $z = 2.5758$ ($59.71$) round up to $60$.*

---

### Exercise 9.21
**Problem:** The estimate of the population proportion is to be within plus or minus .05, with a 95 percent level of confidence. The best estimate of the population proportion is .15. How large a sample is required?

**Given:** $E = 0.05$, $\pi = 0.15$, $95\%$ confidence ($z = 1.96$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.15(0.85)\left(\frac{1.96}{0.05}\right)^2 = 0.1275(1,536.64) = 195.9216 \implies \mathbf{n = 196}.$$

**Answer:** **$n = 196$** ($195.9216$ rounded up).

✔ *Checker: Matches Lind Appendix C ($196$, found by $0.15(0.85)(1.96/0.05)^2 = 195.9216$).*

---

### Exercise 9.22
**Problem:** The estimate of the population proportion is to be within plus or minus .10, with a 99 percent level of confidence. The best estimate of the population proportion is .45. How large a sample is required?

**Given:** $E = 0.10$, $\pi = 0.45$, $99\%$ confidence ($z = 2.58$, or exact $2.5758$).

Using $z = 2.58$:
$$n = 0.45(0.55)\left(\frac{2.58}{0.10}\right)^2 = 0.2475(665.64) = 164.7459 \implies \mathbf{n = 165}.$$

**Answer:** **$n = 165$** ($164.75$ rounded up).

✔ *Checker: Both $z = 2.58$ ($164.75$) and exact $z = 2.5758$ ($164.21$) round up to $165$.*

---

### Exercise 9.23
**Problem:** A survey is being planned to determine the mean amount of time corporation executives watch television. A pilot survey indicated that the mean time per week is 12 hours, with a standard deviation of 3 hours. It is desired to estimate the mean viewing time within one-quarter hour. The 95 percent level of confidence is to be used. How many executives should be surveyed?

**Given:** $\sigma = 3$ hours, $E = 0.25$ hours, $95\%$ confidence ($z = 1.96$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 3}{0.25}\right)^2 = (23.52)^2 = 553.1904 \implies \mathbf{n = 554}\text{ executives}.$$

**Answer:** **$n = 554$ executives** ($553.19$ rounded up).

✔ *Checker: Matches Lind Appendix C ($554$, found by $(1.96 \times 3 / 0.25)^2 = 553.19$).*

---

### Exercise 9.24
**Problem:** A processor of carrots cuts the green top off each carrot, washes the carrots, and inserts six to a package. Twenty packages are inserted in a box for shipment. To test the weight of the boxes, a few were checked. The mean weight was 20.4 pounds; the standard deviation, 0.5 pounds. How many boxes must the processor sample to be 95 percent confident that the sample mean does not differ from the population mean by more than 0.2 pounds?

**Given:** $s = 0.5$ lb, $E = 0.2$ lb, $95\%$ confidence ($z = 1.96$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 0.5}{0.2}\right)^2 = (4.9)^2 = 24.01 \implies \mathbf{n = 25}\text{ boxes (rounded up)}.$$

**Answer:** **$n = 25$ boxes** ($24.01$ rounded up).

✔ *Checker: Recomputed in Python; $(1.96 \times 0.5 / 0.2)^2 = 24.01 \to 25$.*

---

### Exercise 9.25
**Problem:** Suppose the U.S. president wants an estimate of the proportion of the population who support his current policy toward revisions in the health care system. The president wants the estimate to be within .04 of the true proportion. Assume a 95 percent level of confidence. The president's political advisors estimated the proportion supporting the current policy to be .60.
(a) How large of a sample is required?
(b) How large of a sample would be necessary if no estimate were available for the proportion supporting current policy?

**Given:** $E = 0.04$, $95\%$ confidence ($z = 1.96$).

**(a)** With $\pi = 0.60$:
$$n = 0.60(0.40)\left(\frac{1.96}{0.04}\right)^2 = 0.24(2,401) = 576.24 \implies \mathbf{n = 577}.$$

**(b)** With no prior estimate, use $\pi = 0.50$:
$$n = 0.50(0.50)\left(\frac{1.96}{0.04}\right)^2 = 0.25(2,401) = 600.25 \implies \mathbf{n = 601}.$$

**Answer:** (a) **$n = 577$** ($576.24$ rounded up); (b) **$n = 601$** ($600.25$ rounded up).

✔ *Checker: Matches Lind Appendix C ($577$ and $601$).*

---

### Exercise 9.26
**Problem:** Past surveys reveal that 30 percent of tourists going to Las Vegas to gamble spend more than $1,000. The Visitor's Bureau of Las Vegas wants to update this percentage.
(a) The new study is to use the 90 percent confidence level. The estimate is to be within 1 percent of the population proportion. What is the necessary sample size?
(b) The Bureau feels the sample size determined above is too large. What can be done to reduce the sample? Based on your suggestion, recalculate the sample size.

**Given:** $\pi = 0.30$, $90\%$ confidence ($z = 1.65$, or $1.645$), $E = 0.01$.

**(a)** Using $z = 1.65$ (Lind table value):
$$n = 0.30(0.70)\left(\frac{1.65}{0.01}\right)^2 = 0.21(27,225) = 5,717.25 \implies \mathbf{n = 5,718}$$
(or with $z = 1.645$: $n = 0.21(1.645/0.01)^2 = 5,682.65 \implies \mathbf{5,683}$).

**(b)** To reduce the required sample size, the Bureau can **increase the allowable margin of error $E$** (for example, from $1\%$ to $2\%$ or $3\%$) or lower the confidence level. Increasing the allowable error to $E = 0.02$ ($2\%$) reduces $n$ by a factor of $4$:
$$n = 0.30(0.70)\left(\frac{1.65}{0.02}\right)^2 = 0.21(6,806.25) = 1,429.31 \implies \mathbf{n = 1,430}\quad (\text{or }1,421\text{ with }z = 1.645).$$

**Answer:** (a) **$n = 5,718$** using $z = 1.65$ (or **$5,683$** using $z = 1.645$); (b) increase the allowable error $E$ (e.g., to $E = 0.02$, which reduces $n$ to **$1,430$**).

✔ *Checker: Recomputed in Python; $0.21 \times 165^2 = 5717.25$.*

---

## Lind — Chapter 9, Section 9.6: Finite-Population Correction Factor

### Exercise 9.27
**Problem:** Thirty-six items are randomly selected from a population of 300 items. The sample mean is 35 and the sample standard deviation 5. Develop a 95 percent confidence interval for the population mean.

**Given:** $N = 300$, $n = 36$, $\bar{X} = 35$, $s = 5$, $95\%$ confidence level.

📘 Since $\sigma$ is unknown, use $t$ with $df = 36 - 1 = 35$ at $95\%$ confidence: from Appendix B.2, $t = 2.030$. Since $n/N = 36/300 = 0.12 > 0.05$, apply the finite-population correction factor:
$$\bar{X} \pm t \frac{s}{\sqrt{n}} \sqrt{\frac{N - n}{N - 1}} = 35 \pm 2.030 \left(\frac{5}{\sqrt{36}}\right) \sqrt{\frac{300 - 36}{300 - 1}} = 35 \pm 1.6917(0.93965) = 35 \pm 1.590.$$
Endpoints: **$33.41$ and $36.59$**.

**Answer:** **$33.41$ to $36.59$**.

✔ *Checker: Matches Lind Appendix C (listed under item 19 on p. 797: $33.41$ and $36.59$, found by $35 \pm 2.030(5/\sqrt{36})\sqrt{(300-36)/(300-1)}$).*

---

### Exercise 9.28
**Problem:** Forty-nine items are randomly selected from a population of 500 items. The sample mean is 40 and the sample standard deviation 9. Develop a 99 percent confidence interval for the population mean.

**Given:** $N = 500$, $n = 49$, $\bar{X} = 40$, $s = 9$, $99\%$ confidence level.

📘 With $df = 49 - 1 = 48$ at $99\%$ confidence, Appendix B.2 gives $t = 2.682$:
$$40 \pm 2.682 \left(\frac{9}{\sqrt{49}}\right) \sqrt{\frac{500 - 49}{500 - 1}} = 40 \pm 3.4483(0.95069) = 40 \pm 3.278 = \mathbf{36.72\text{ to }43.28}$$
(or using $z = 2.58$: $40 \pm 2.58(9/7)(0.95069) = 40 \pm 3.15 = 36.85$ to $43.15$).

**Answer:** **$36.72$ to $43.28$** (using $t_{48} = 2.682$).

✔ *Checker: Recomputed in Python; $t_{48, 0.005} = 2.6822$, half-width $= 3.2782$.*

---

### Exercise 9.29
**Problem:** The attendance at the Savannah Colts minor league baseball game last night was 400. A random sample of 50 of those in attendance revealed that the mean number of soft drinks consumed per person was 1.86, with a standard deviation of 0.50. Develop a 99 percent confidence interval for the mean number of soft drinks consumed per person.

**Given:** $N = 400$, $n = 50$, $\bar{X} = 1.86$, $s = 0.50$, $99\%$ confidence level.

📘 From Appendix B.2, for $df = 50 - 1 = 49$ at $99\%$ confidence, $t = 2.680$:
$$1.86 \pm 2.680 \left(\frac{0.50}{\sqrt{50}}\right) \sqrt{\frac{400 - 50}{400 - 1}} = 1.86 \pm 0.18950(0.93659) = 1.86 \pm 0.177 = \mathbf{1.683\text{ to }2.037}.$$

**Answer:** **$1.683$ to $2.037$ soft drinks**.

✔ *Checker: Matches Lind Appendix C (listed under item 21 on p. 797: $1.683$ and $2.037$).*

---

### Exercise 9.30
**Problem:** There are 300 welders employed at Maine Shipyards Corporation. A sample of 30 welders revealed that 18 graduated from a registered welding course. Construct the 95 percent confidence interval for the proportion of all welders who graduated from a registered welding course.

**Given:** $N = 300$, $n = 30$, $X = 18 \implies p = 18/30 = 0.60$, $95\%$ confidence level ($z = 1.96$).

Apply the finite-population correction factor $\sqrt{(300 - 30)/(300 - 1)}$:
$$0.60 \pm 1.96 \sqrt{\frac{0.60(0.40)}{30}} \sqrt{\frac{300 - 30}{300 - 1}} = 0.60 \pm 1.96(0.089443)(0.95027) = 0.60 \pm 0.1666 = \mathbf{0.4334\text{ to }0.7666}\text{ (or }\mathbf{0.433\text{ to }0.767}\text{)}.$$

**Answer:** **$0.4334$ to $0.7666$** (or **$0.433$ to $0.767$**).

✔ *Checker: Recomputed in Python; $0.60 \pm 0.16655 = [0.4334, 0.7666]$.*

---

## Lind — Chapter 9: Chapter Exercises

### Exercise 9.31
**Problem:** A random sample of 85 group leaders, supervisors, and similar personnel at General Motors revealed that, on average, they spent 6.5 years on the job before being promoted. The standard deviation of the sample was 1.7 years. Construct a 95 percent confidence interval.

**Given:** $n = 85$, $\bar{X} = 6.5$ years, $s = 1.7$ years, $95\%$ confidence level.

📘 From Appendix B.2, for $df = 85 - 1 = 84$ at $95\%$ confidence, $t = 1.989$:
$$6.5 \pm 1.989 \left(\frac{1.7}{\sqrt{85}}\right) = 6.5 \pm 1.989(0.18439) = 6.5 \pm 0.367 = \mathbf{6.13\text{ to }6.87\text{ years}}.$$

**Answer:** **$6.13$ to $6.87$ years**.

✔ *Checker: Matches Lind Appendix C ($6.13$ years to $6.87$ years, found by $6.5 \pm 1.989(1.7/\sqrt{85})$).*

---

### Exercise 9.32
**Problem:** A state meat inspector in Iowa has been given the assignment of estimating the mean net weight of packages of ground chuck labeled "3 pounds." Of course, he realizes that the weights cannot be precisely 3 pounds. A sample of 36 packages reveals the mean weight to be 3.01 pounds, with a standard deviation of 0.03 pounds.
(a) What is the estimated population mean?
(b) Determine a 95 percent confidence interval for the population mean.

**Given:** $n = 36$, $\bar{X} = 3.01$ lb, $s = 0.03$ lb, $95\%$ confidence level.

**(a)** The estimated population mean is **$3.01$ pounds**.

**(b)** 📘 From Appendix B.2, for $df = 36 - 1 = 35$ at $95\%$ confidence, $t = 2.030$:
$$3.01 \pm 2.030 \left(\frac{0.03}{\sqrt{36}}\right) = 3.01 \pm 2.030(0.005) = 3.01 \pm 0.01015 = \mathbf{3.000\text{ to }3.020\text{ pounds}}.$$

**Answer:** (a) $3.01$ pounds; (b) **$3.000$ to $3.020$ pounds** ($2.99985$ to $3.02015$).

✔ *Checker: Recomputed in Python; $2.030 \times 0.005 = 0.01015$.*

---

### Exercise 9.33
**Problem:** As part of their business promotional package, the Milwaukee Chamber of Commerce would like an estimate of the mean cost per month of a one-bedroom apartment. A random sample of 40 apartments currently available for lease showed the mean cost per month was $323. The standard deviation of the sample was $25.
(a) Develop a 98 percent confidence interval for the population mean.
(b) Would it be reasonable to conclude that the population mean is $350 per month?

**Given:** $n = 40$, $\bar{X} = \$323$, $s = \$25$, $98\%$ confidence level.

**(a)** 📘 From Appendix B.2, for $df = 40 - 1 = 39$ at $98\%$ confidence, $t = 2.426$:
$$\$323 \pm 2.426 \left(\frac{\$25}{\sqrt{40}}\right) = \$323 \pm 2.426(3.95285) = \$323 \pm \$9.59 = \mathbf{\$313.41\text{ to }\$332.59}.$$

**(b)** **No**, $\$350$ is not reasonable because it lies well outside the $98\%$ confidence interval ($\$313.41$ to $\$332.59$).

**Answer:** (a) **$\$313.41$ to $\$332.59$**; (b) no, $\$350$ is outside the confidence interval.

✔ *Checker: Matches Lind Appendix C ($\$313.41$ and $\$332.59$; $\$350$ is not reasonable).*

---

### Exercise 9.34
**Problem:** A recent survey of 50 executives who were laid off during a recent recession revealed it took a mean of 26 weeks for them to find another position. The standard deviation of the sample was 6.2 weeks. Construct a 95 percent confidence interval for the population mean. Is it reasonable that the population mean is 28 weeks? Justify your answer.

**Given:** $n = 50$, $\bar{X} = 26$ weeks, $s = 6.2$ weeks, $95\%$ confidence level.

📘 From Appendix B.2, for $df = 50 - 1 = 49$ at $95\%$ confidence, $t = 2.010$:
$$26 \pm 2.010 \left(\frac{6.2}{\sqrt{50}}\right) = 26 \pm 2.010(0.87681) = 26 \pm 1.76 = \mathbf{24.24\text{ to }27.76\text{ weeks}}.$$
**No**, it is not reasonable that the population mean is $28$ weeks because $28$ lies outside the $95\%$ confidence interval ($24.24$ to $27.76$).

**Answer:** **$24.24$ to $27.76$ weeks**; no, 28 weeks is outside the confidence interval.

✔ *Checker: Recomputed in Python; $2.00958 \times 6.2 / \sqrt{50} = 1.762$.*

---

### Exercise 9.35
**Problem:** Marty Rowatti recently assumed the position of director of the YMCA of South Jersey. He would like some current data on how long current members of the YMCA have been members. To investigate, suppose he selects a random sample of 40 current members. The mean length of membership of those included in the sample is 8.32 years and the standard deviation is 3.07 years.
(a) What is the mean of the population?
(b) Develop a 90 percent confidence interval for the population mean.
(c) The previous director, in the summary report she prepared as she retired, indicated the mean length of membership was now "almost 10 years." Does the sample information substantiate this claim? Cite evidence.

**Given:** $n = 40$, $\bar{X} = 8.32$ years, $s = 3.07$ years, $90\%$ confidence level.

**(a)** The population mean $\mu$ is **unknown** (estimated by $\bar{X} = 8.32$ years).

**(b)** 📘 From Appendix B.2, for $df = 39$ at $90\%$ confidence, $t = 1.685$:
$$8.32 \pm 1.685 \left(\frac{3.07}{\sqrt{40}}\right) = 8.32 \pm 1.685(0.48541) = 8.32 \pm 0.818 = \mathbf{7.50\text{ to }9.14\text{ years}}.$$

**(c)** **No**, $10$ years is not reasonable because $10$ lies outside (above) the $90\%$ confidence interval ($7.50$ to $9.14$ years).

**Answer:** (a) Unknown; (b) **$7.50$ to $9.14$ years**; (c) no, 10 years is outside the confidence interval.

✔ *Checker: Matches Lind Appendix C (Unknown; between $7.50$ and $9.14$; $10$ is not reasonable).*

---

### Exercise 9.36
**Problem:** The American Restaurant Association collected information on the number of meals eaten outside the home per week by young married couples. A survey of 60 couples showed the sample mean number of meals eaten outside the home was 2.76 meals per week, with a standard deviation of 0.75 meals per week. Construct a 97 percent confidence interval for the population mean.

**Given:** $n = 60$, $\bar{X} = 2.76$, $s = 0.75$, $97\%$ confidence level.

For a $97\%$ confidence interval ($0.4850$ in each half; two-tailed $\alpha = 0.03$), Appendix B.1 gives $z = 2.17$ (or exact $t_{59, 0.015} = 2.226$):
- Using $z = 2.17$:
  $$2.76 \pm 2.17 \left(\frac{0.75}{\sqrt{60}}\right) = 2.76 \pm 2.17(0.096825) = 2.76 \pm 0.210 = \mathbf{2.55\text{ to }2.97\text{ meals}}.$$
- Using exact $t_{59} = 2.226$:
  $$2.76 \pm 2.226(0.096825) = 2.76 \pm 0.216 = \mathbf{2.54\text{ to }2.98\text{ meals}}.$$

**Answer:** **$2.55$ to $2.97$ meals** (using $z = 2.17$) or **$2.54$ to $2.98$ meals** (using $t_{59} = 2.226$).

✔ *Checker: Recomputed in Python; SE $= 0.096825$.*

---

### Exercise 9.37
**Problem:** The National Collegiate Athletic Association (NCAA) reported that the mean number of hours spent per week on coaching and recruiting by college football assistant coaches during the season was 70. A random sample of 50 assistant coaches showed the sample mean to be 68.6 hours, with a standard deviation of 8.2 hours.
(a) Using the sample data, construct a 99 percent confidence interval for the population mean.
(b) Does the 99 percent confidence interval include the value suggested by the NCAA? Interpret this result.
(c) Suppose you decided to switch from a 99 to a 95 percent confidence interval. Without performing any calculations, will the interval increase, decrease, or stay the same? Which of the values in the formula will change?

**Given:** $n = 50$, $\bar{X} = 68.6$ hours, $s = 8.2$ hours, $99\%$ confidence level.

**(a)** 📘 From Appendix B.2, for $df = 49$ at $99\%$ confidence, $t = 2.680$:
$$68.6 \pm 2.680 \left(\frac{8.2}{\sqrt{50}}\right) = 68.6 \pm 2.680(1.15966) = 68.6 \pm 3.108 = \mathbf{65.49\text{ to }71.71\text{ hours}}.$$

**(b)** **Yes**, the $99\%$ confidence interval ($65.49$ to $71.71$) includes the NCAA value of $70$ hours, so the NCAA's figure of $70$ hours per week is reasonable.

**(c)** Switching from $99\%$ to $95\%$ confidence will **decrease (narrow)** the width of the interval. The critical $t$-value in the formula will change from **$2.680$ to $2.010$**.

**Answer:** (a) **$65.49$ to $71.71$ hours**; (b) yes, 70 is inside the interval so the NCAA value is reasonable; (c) the interval width will decrease because $t$ changes from $2.680$ to $2.010$.

✔ *Checker: Matches Lind Appendix C ($65.49$ up to $71.71$; $2.680$ changes to $2.010$).*

---

### Exercise 9.38
**Problem:** The Human Relations Department of Electronics Inc. would like to include a dental plan as part of the benefits package. The question is: How much does a typical employee and his or her family spend per year on dental expenses? A sample of 45 employees reveals the mean amount spent last year was $1,820, with a standard deviation of $660.
(a) Construct a 95 percent confidence interval for the population mean.
(b) The information from part (a) was given to the president of Electronics Inc. He indicated he could afford $1,700 of dental expenses per employee. Is it possible that the population mean could be $1,700? Justify your answer.

**Given:** $n = 45$, $\bar{X} = \$1,820$, $s = \$660$, $95\%$ confidence level.

**(a)** 📘 From Appendix B.2, for $df = 45 - 1 = 44$ at $95\%$ confidence, $t = 2.015$:
$$\$1,820 \pm 2.015 \left(\frac{\$660}{\sqrt{45}}\right) = \$1,820 \pm 2.015(98.38699) = \$1,820 \pm \$198.25 = \mathbf{\$1,621.75\text{ to }\$2,018.25}.$$

**(b)** **Yes**, it is possible that the population mean is $\$1,700$ because $\$1,700$ falls inside the $95\%$ confidence interval ($\$1,621.75$ to $\$2,018.25$).

**Answer:** (a) **$\$1,621.75$ to $\$2,018.25$**; (b) yes, $\$1,700$ is inside the 95% confidence interval.

✔ *Checker: Recomputed in Python; $t_{44, 0.025} = 2.01537$, half-width $= 198.29$.*

---

### Exercise 9.39
**Problem:** A student conducted a study and reported that the 95 percent confidence interval for the mean ranged from 46 to 54. He was sure that the mean of the sample was 50, that the standard deviation of the sample was 16, and that the sample was at least 30, but could not remember the exact number. Can you help him out?

**Given:** $95\%$ CI is $[46, 54]$, $\bar{X} = 50$, $s = 16$, margin of error $E = 54 - 50 = 4$.

Using $z = 1.96$ (as in Lind Appendix C):
$$E = z \frac{s}{\sqrt{n}} \implies 4 = 1.96 \left(\frac{16}{\sqrt{n}}\right) \implies \sqrt{n} = \frac{1.96 \times 16}{4} = 7.84 \implies n = (7.84)^2 = 61.4656 \implies \mathbf{n = 61\text{ (or }62\text{)}}.$$
(Note: Using the $t$ distribution with $df = 63$, $t = 2.000$, which gives $2.000(16/\sqrt{64}) = 4.00$ exactly at **$n = 64$**.)

**Answer:** **$n = 61$** (or $62$ using $z = 1.96$, or **$n = 64$** using $t = 2.000$).

✔ *Checker: Matches Lind Appendix C ($61$, found by $1.96(16/\sqrt{n}) = 4$).*

---

### Exercise 9.40
**Problem:** A recent study by the American Automobile Dealers Association revealed the mean amount of profit per car sold for a sample of 20 dealers was $290, with a standard deviation of $125. Develop a 95 percent confidence interval for the population mean.

**Given:** $n = 20$, $\bar{X} = \$290$, $s = \$125$, $95\%$ confidence level.

📘 From Appendix B.2, for $df = 20 - 1 = 19$ at $95\%$ confidence, $t = 2.093$:
$$\$290 \pm 2.093 \left(\frac{\$125}{\sqrt{20}}\right) = \$290 \pm 2.093(27.95085) = \$290 \pm \$58.50 = \mathbf{\$231.50\text{ to }\$348.50}.$$

**Answer:** **$\$231.50$ to $\$348.50$**.

✔ *Checker: Recomputed in Python; $2.093 \times 125 / \sqrt{20} = 58.501$.*

---

### Exercise 9.41
**Problem:** A study of 25 graduates of four-year colleges by the American Banker's Association revealed the mean amount owed by a student in student loans was $14,381. The standard deviation of the sample was $1,892. Construct a 90 percent confidence interval for the population mean. Is it reasonable to conclude that the mean of the population is actually $15,000? Tell why or why not.

**Given:** $n = 25$, $\bar{X} = \$14,381$, $s = \$1,892$, $90\%$ confidence level.

📘 From Appendix B.2, for $df = 25 - 1 = 24$ at $90\%$ confidence, $t = 1.711$:
$$\$14,381 \pm 1.711 \left(\frac{\$1,892}{\sqrt{25}}\right) = \$14,381 \pm 1.711(378.40) = \$14,381 \pm \$647.44 = \mathbf{\$13,733.56\text{ to }\$15,028.44}\text{ (or }\mathbf{\$13,734\text{ to }\$15,028}\text{)}.$$
**Yes**, $\$15,000$ is reasonable because it falls inside the $90\%$ confidence interval.

**Answer:** **$\$13,734$ to $\$15,028$** ($\$13,733.56$ to $\$15,028.44$); yes, $\$15,000$ is inside the interval.

✔ *Checker: Matches Lind Appendix C (Between $\$13,734$ up to $\$15,028$; $15,000$ is reasonable).*

---

### Exercise 9.42
**Problem:** An important factor in selling a residential property is the number of people who look through the home. A sample of 15 homes recently sold in the Buffalo, New York, area revealed the mean number looking through each home was 24 and the standard deviation of the sample was 5 people. Develop a 98 percent confidence interval for the population mean.

**Given:** $n = 15$, $\bar{X} = 24$, $s = 5$, $98\%$ confidence level.

📘 From Appendix B.2, for $df = 15 - 1 = 14$ at $98\%$ confidence, $t = 2.624$:
$$24 \pm 2.624 \left(\frac{5}{\sqrt{15}}\right) = 24 \pm 2.624(1.29099) = 24 \pm 3.388 = \mathbf{20.61\text{ to }27.39\text{ people}}.$$

**Answer:** **$20.61$ to $27.39$ people**.

✔ *Checker: Recomputed in Python; $2.624 \times 5 / \sqrt{15} = 3.3876$.*

---

### Exercise 9.43
**Problem:** Warren County Telephone Company claims in its annual report that "the typical customer spends $60 per month on local and long-distance service." A sample of 12 subscribers revealed the following amounts spent last month.
$64 $66 $64 $66 $59 $62 $67 $61 $64 $58 $54 $66
(a) What is the point estimate of the population mean?
(b) Develop a 90 percent confidence interval for the population mean.
(c) Is the company's claim that the "typical customer" spends $60 per month reasonable? Justify your answer.

**Given:** $n = 12$ monthly bills: $64, 66, 64, 66, 59, 62, 67, 61, 64, 58, 54, 66$; $90\%$ confidence level.

**(a)** Point estimate of the population mean:
$$\bar{X} = \frac{751}{12} = \mathbf{\$62.583}\text{ (or }\$62.58\text{)}.$$
Sample standard deviation:
$$s = \sqrt{\frac{\sum (X - 62.5833)^2}{11}} = \sqrt{\frac{170.9167}{11}} \approx \mathbf{\$3.9418}.$$

**(b)** 📘 From Appendix B.2, for $df = 11$ at $90\%$ confidence, $t = 1.796$:
$$62.5833 \pm 1.796 \left(\frac{3.9418}{\sqrt{12}}\right) = 62.5833 \pm 1.796(1.1379) = 62.5833 \pm 2.044 = \mathbf{\$60.54\text{ to }\$64.63}.$$

**(c)** **No**, $\$60$ is not reasonable because $\$60.00$ lies outside (below) the $90\%$ confidence interval ($\$60.54$ to $\$64.63$).

**Answer:** (a) $\$62.58$ ($\$62.583$); (b) **$\$60.54$ to $\$64.63$**; (c) no, $\$60$ is outside the confidence interval.

✔ *Checker: Matches Lind Appendix C ($\$62.583$; between $\$60.54$ and $\$64.63$; $\$60$ is not reasonable).*

---

### Exercise 9.44
**Problem:** The manufacturer of a new line of ink-jet printers would like to include as part of its advertising the number of pages a user can expect from a print cartridge. A sample of 10 cartridges revealed the following number of pages printed.
2,698 2,028 2,474 2,395 2,372 2,475 1,927 3,006 2,334 2,379
(a) What is the point estimate of the population mean?
(b) Develop a 95 percent confidence interval for the population mean.

**Given:** $n = 10$ page counts: $2698, 2028, 2474, 2395, 2372, 2475, 1927, 3006, 2334, 2379$; $95\%$ confidence level.

**(a)** Point estimate of the population mean:
$$\bar{X} = \frac{24,088}{10} = \mathbf{2,408.8\text{ pages}}.$$
Sample standard deviation:
$$s = \sqrt{\frac{\sum (X - 2408.8)^2}{9}} = \sqrt{\frac{801,603.6}{9}} = \sqrt{89,067.0667} \approx \mathbf{298.4411\text{ pages}}.$$

**(b)** 📘 From Appendix B.2, for $df = 9$ at $95\%$ confidence, $t = 2.262$:
$$2,408.8 \pm 2.262 \left(\frac{298.4411}{\sqrt{10}}\right) = 2,408.8 \pm 2.262(94.3754) = 2,408.8 \pm 213.48 = \mathbf{2,195.32\text{ to }2,622.28\text{ pages}}.$$

**Answer:** (a) $2,408.8$ pages; (b) **$2,195.32$ to $2,622.28$ pages**.

✔ *Checker: Recomputed in Python; $\bar{X} = 2408.8, s = 298.4411, t = 2.262$, CI $[2195.32, 2622.28]$.*

---

### Exercise 9.45
**Problem:** Dr. Susan Benner is an industrial psychologist. She is currently studying stress among executives of Internet companies. She has developed a questionnaire that she believes measures stress. A score above 80 indicates stress at a dangerous level. A random sample of 15 executives revealed the following stress level scores.
94 78 83 90 78 99 97 90 97 90 93 94 100 75 84
(a) Find the mean stress level for this sample. What is the point estimate of the population mean?
(b) Construct a 95 percent confidence level for the population mean.
(c) Is it reasonable to conclude that Internet executives have a mean stress level in the dangerous level, according to Dr. Benner's test?

**Given:** $n = 15$ scores: $94, 78, 83, 90, 78, 99, 97, 90, 97, 90, 93, 94, 100, 75, 84$; $95\%$ confidence level.

**(a)** Sample mean (point estimate of $\mu$):
$$\bar{X} = \frac{1,342}{15} = \mathbf{89.4667}.$$
Sample standard deviation:
$$s = \sqrt{\frac{\sum (X - 89.4667)^2}{14}} = \sqrt{\frac{914.7333}{14}} \approx \mathbf{8.0832}.$$

**(b)** 📘 From Appendix B.2, for $df = 14$ at $95\%$ confidence, $t = 2.145$:
$$89.4667 \pm 2.145 \left(\frac{8.0832}{\sqrt{15}}\right) = 89.4667 \pm 2.145(2.08707) = 89.4667 \pm 4.4768 = \mathbf{84.99\text{ to }93.94}.$$

**(c)** **Yes**, because the entire $95\%$ confidence interval ($84.99$ to $93.94$) lies above the dangerous threshold of $80$.

**Answer:** (a) $89.4667$; (b) **$84.99$ to $93.94$**; (c) yes, even the lower limit ($84.99$) is above 80.

✔ *Checker: Matches Lind Appendix C ($89.4667$; between $84.99$ and $93.94$; yes).*

---

### Exercise 9.46
**Problem:** As a condition of employment, Fashion Industries applicants must pass a drug test. Of the last 220 applicants, 14 failed the test. Develop a 99 percent confidence interval for the proportion of applicants that fail the test. Would it be reasonable to conclude that more than 10 percent of the applicants are now failing the test?

**Given:** $n = 220$, $X = 14 \implies p = 14/220 = 0.06364$, $99\%$ confidence level ($z = 2.58$).

Compute the $99\%$ confidence interval:
$$0.06364 \pm 2.58 \sqrt{\frac{0.06364(0.93636)}{220}} = 0.06364 \pm 2.58(0.016457) = 0.06364 \pm 0.04246 = \mathbf{0.0212\text{ to }0.1061}\text{ (or }\mathbf{0.021\text{ to }0.106}\text{)}.$$
Because $0.10$ ($10\%$) is inside the interval (and most of the interval lies below $0.10$), **we cannot definitively conclude that more than $10\%$ are failing**, though a rate slightly above $10\%$ (up to $10.6\%$) is possible.

**Answer:** **$0.0212$ to $0.1061$** ($2.12\%$ to $10.61\%$); since $0.10$ is inside the interval, it is possible the true rate exceeds $10\%$, so we cannot rule it out, nor can we conclude it is definitely above $10\%$.

✔ *Checker: Recomputed in Python; $p = 0.063636$, SE $= 0.016457$, CI $[0.0212, 0.1061]$.*

---

### Exercise 9.47
**Problem:** Fashion Industries randomly tests its employees throughout the year. Last year in the 400 random tests conducted, 14 employees failed the test. Would it be reasonable to conclude that less than 5 percent of the employees are not able to pass the random drug test? Explain.

**Given:** $n = 400$, $X = 14 \implies p = 14/400 = 0.035$, $99\%$ confidence level ($z = 2.58$, as in Lind Appendix C; or $95\%$ with $z = 1.96$).

- **At $99\%$ confidence ($z = 2.58$, per Lind Appendix C):**
  $$0.035 \pm 2.58 \sqrt{\frac{0.035(0.965)}{400}} = 0.035 \pm 2.58(0.009189) = 0.035 \pm 0.0237 = \mathbf{0.0113\text{ to }0.0587}\text{ (or }\mathbf{0.011\text{ to }0.059}\text{)}.$$
  Because $0.05$ ($5\%$) is inside the $99\%$ confidence interval ($0.011$ to $0.059$), **it is not reasonable to conclude with $99\%$ confidence that fewer than $5\%$ fail**.
- *(Note: At $95\%$ confidence with $z = 1.96$, $0.035 \pm 0.0180 = \mathbf{0.017\text{ to }0.053}$, which also includes $0.05$.)*

**Answer:** Confidence interval is **$0.011$ to $0.059$** ($99\%$ CI) or **$0.017$ to $0.053$** ($95\%$ CI); **no**, it is not reasonable to conclude that fewer than $5\%$ fail because $0.05$ is inside the interval.

✔ *Checker: Matches Lind Appendix C (between $0.011$ and $0.059$; not reasonable because $0.05$ is inside the interval).*

---

### Exercise 9.48
**Problem:** During a national debate on changes to health care, a cable news service performs an opinion poll of 500 small-business owners. It shows that 65 percent of small-business owners do not approve of the changes. Develop a 95 percent confidence interval for the proportion opposing health care changes. Comment on the result.

**Given:** $n = 500$, $p = 0.65$, $95\%$ confidence level ($z = 1.96$).

$$0.65 \pm 1.96 \sqrt{\frac{0.65(0.35)}{500}} = 0.65 \pm 1.96(0.021331) = 0.65 \pm 0.0418 = \mathbf{0.6082\text{ to }0.6918}\text{ (or }\mathbf{0.608\text{ to }0.692}\text{)}.$$
Because even the lower limit ($60.8\%$) is well above $50\%$, a clear majority of small-business owners oppose the health care changes.

**Answer:** **$0.6082$ to $0.6918$** ($60.8\%$ to $69.2\%$); a clear majority oppose the changes.

✔ *Checker: Recomputed in Python; $0.65 \pm 0.04181 = [0.6082, 0.6918]$.*

---

### Exercise 9.49
**Problem:** There are 20,000 eligible voters in York County, South Carolina. A random sample of 500 York County voters revealed 350 plan to vote to return Louella Miller to the state senate. Construct a 99 percent confidence interval for the proportion of voters in the county who plan to vote for Ms. Miller. From this sample information, can you confirm she will be re-elected?

**Given:** $N = 20,000$, $n = 500$, $X = 350 \implies p = 350/500 = 0.70$, $99\%$ confidence level ($z = 2.58$).

Since $n/N = 500/20,000 = 0.025 < 0.05$, the FPC is optional ($\sqrt{19,500/19,999} = 0.9874$):
- **Without FPC:**
  $$0.70 \pm 2.58 \sqrt{\frac{0.70(0.30)}{500}} = 0.70 \pm 2.58(0.020494) = 0.70 \pm 0.0529 = \mathbf{0.6471\text{ to }0.7529}.$$
- **With FPC:**
  $$0.70 \pm 0.0529(0.9874) = 0.70 \pm 0.0522 = \mathbf{0.6478\text{ to }0.7522}.$$
**Yes**, because the entire $99\%$ confidence interval is well above $0.50$ ($50\%$), we can confirm she will be re-elected.

**Answer:** **$0.647$ to $0.753$** ($0.648$ to $0.752$ with FPC); yes, she will be re-elected because the lower bound is well above $0.50$.

✔ *Checker: Recomputed in Python; SE $= 0.020494$.*

---

### Exercise 9.50
**Problem:** In a poll to estimate presidential popularity, each person in a random sample of 1,000 voters was asked to agree with one of the following statements:
1. The president is doing a good job.
2. The president is doing a poor job.
3. I have no opinion.
A total of 560 respondents selected the first statement, indicating they thought the president was doing a good job.
(a) Construct a 95 percent confidence interval for the proportion of respondents who feel the president is doing a good job.
(b) Based on your interval in part (a), is it reasonable to conclude that a majority (more than half) of the population believes the president is doing a good job?

**Given:** $n = 1,000$, $X = 560 \implies p = 0.560$, $95\%$ confidence level ($z = 1.96$).

**(a)** $95\%$ confidence interval:
$$0.560 \pm 1.96 \sqrt{\frac{0.560(0.440)}{1,000}} = 0.560 \pm 1.96(0.015697) = 0.560 \pm 0.0308 = \mathbf{0.5292\text{ to }0.5908}\text{ (or }\mathbf{0.529\text{ to }0.591}\text{)}.$$

**(b)** **Yes**, because the entire confidence interval ($0.529$ to $0.591$) lies above $0.500$.

**Answer:** (a) **$0.529$ to $0.591$** ($0.5292$ to $0.5908$); (b) yes, the lower limit ($0.529$) is above $0.50$.

✔ *Checker: Recomputed in Python; $0.56 \pm 0.03077 = [0.5292, 0.5908]$.*

---

### Exercise 9.51
**Problem:** Police Chief Edward Wilkin of River City reports 500 traffic citations were issued last month. A sample of 35 of these citations showed the mean amount of the fine was $54, with a standard deviation of $4.50. Construct a 95 percent confidence interval for the mean amount of a citation in River City.

**Given:** $N = 500$, $n = 35$, $\bar{X} = \$54.00$, $s = \$4.50$, $95\%$ confidence level.

📘 From Appendix B.2, for $df = 35 - 1 = 34$ at $95\%$ confidence, $t = 2.032$. Applying the FPC since $n/N = 35/500 = 0.07 > 0.05$:
$$\$54.00 \pm 2.032 \left(\frac{\$4.50}{\sqrt{35}}\right) \sqrt{\frac{500 - 35}{500 - 1}} = \$54.00 \pm 1.54567(0.96533) = \$54.00 \pm \$1.49 = \mathbf{\$52.51\text{ to }\$55.49}.$$

**Answer:** **$\$52.51$ to $\$55.49$**.

✔ *Checker: Matches Lind Appendix C (listed as item 49 on p. 797 due to the 2-item shift: $\$52.51$ and $\$55.49$).*

---

### Exercise 9.52
**Problem:** The First National Bank of Wilson has 650 checking account customers. A recent sample of 50 of these customers showed 26 have a Visa card with the bank. Construct the 99 percent confidence interval for the proportion of checking account customers who have a Visa card with the bank.

**Given:** $N = 650$, $n = 50$, $X = 26 \implies p = 26/50 = 0.52$, $99\%$ confidence level ($z = 2.58$).

Since $n/N = 50/650 = 0.0769 > 0.05$, apply the FPC:
$$0.52 \pm 2.58 \sqrt{\frac{0.52(0.48)}{50}} \sqrt{\frac{650 - 50}{650 - 1}} = 0.52 \pm 2.58(0.070654)(0.96151) = 0.52 \pm 0.1753 = \mathbf{0.3447\text{ to }0.6953}\text{ (or }\mathbf{0.345\text{ to }0.695}\text{)}.$$

**Answer:** **$0.345$ to $0.695$** ($0.3447$ to $0.6953$).

✔ *Checker: Recomputed in Python; $0.52 \pm 0.17527 = [0.3447, 0.6953]$.*

---

### Exercise 9.53
**Problem:** It is estimated that 60 percent of U.S. households subscribe to cable TV. You would like to verify this statement for your class in mass communications. If you want your estimate to be within 5 percentage points, with a 95 percent level of confidence, how large of a sample is required?

**Given:** $\pi = 0.60$, $E = 0.05$, $95\%$ confidence ($z = 1.96$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.60(0.40)\left(\frac{1.96}{0.05}\right)^2 = 0.24(1,536.64) = 368.7936 \implies \mathbf{n = 369}.$$

**Answer:** **$n = 369$** ($368.79$ rounded up).

✔ *Checker: Matches Lind Appendix C (listed as item 51 on p. 797: $369$, found by $0.60(1-0.60)(1.96/0.05)^2$).*

---

### Exercise 9.54
**Problem:** You need to estimate the mean number of travel days per year for outside salespeople. The mean of a small pilot study was 150 days, with a standard deviation of 14 days. If you must estimate the population mean within 2 days, how many outside salespeople should you sample? Use the 90 percent confidence level.

**Given:** $s = 14$ days, $E = 2$ days, $90\%$ confidence ($z = 1.65$, or $1.645$).

Using $z = 1.65$ (Lind table value):
$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.65 \times 14}{2}\right)^2 = (11.55)^2 = 133.4025 \implies \mathbf{n = 134}\text{ salespeople}$$
(or with $z = 1.645$: $n = (1.645 \times 7)^2 = 132.595 \implies \mathbf{133}$).

**Answer:** **$n = 134$** (using $z = 1.65$) or **$n = 133$** (using $z = 1.645$).

✔ *Checker: Recomputed in Python; $(1.65 \times 7)^2 = 133.4025$.*

---

### Exercise 9.55
**Problem:** You are to conduct a sample survey to determine the mean family income in a rural area of central Florida. The question is, how many families should be sampled? In a pilot sample of 10 families, the standard deviation of the sample was $500. The sponsor of the survey wants you to use the 95 percent confidence level. The estimate is to be within $100. How many families should be interviewed?

**Given:** $s = \$500$, $E = \$100$, $95\%$ confidence ($z = 1.96$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 500}{100}\right)^2 = (9.8)^2 = 96.04 \implies \mathbf{n = 97}\text{ families}.$$

**Answer:** **$n = 97$ families** ($96.04$ rounded up).

✔ *Checker: Matches Lind Appendix C (listed as item 53 on p. 797: $97$, found by $[(1.96 \times 500)/100]^2$).*

---

### Exercise 9.56
**Problem:** Families USA, a monthly magazine that discusses issues related to health and health costs, surveyed 20 of its subscribers. It found that the annual health insurance premiums for a family with coverage through an employer averaged $10,979. The standard deviation of the sample was $1,000.
(a) Based on this sample information, develop a 90 percent confidence interval for the population mean yearly premium.
(b) How large a sample is needed to find the population mean within $250 at 99 percent confidence?

**Given:** $n = 20$, $\bar{X} = \$10,979$, $s = \$1,000$.

**(a)** 📘 For $df = 19$ at $90\%$ confidence, Appendix B.2 gives $t = 1.729$:
$$\$10,979 \pm 1.729 \left(\frac{\$1,000}{\sqrt{20}}\right) = \$10,979 \pm 1.729(223.6068) = \$10,979 \pm \$386.62 = \mathbf{\$10,592.38\text{ to }\$11,365.62}.$$

**(b)** With $E = \$250$ and $99\%$ confidence ($z = 2.58$):
$$n = \left(\frac{2.58 \times 1,000}{250}\right)^2 = (10.32)^2 = 106.5024 \implies \mathbf{n = 107}\text{ subscribers}\quad (\text{or }107\text{ with }z = 2.5758:\; 106.16 \to 107).$$

**Answer:** (a) **$\$10,592.38$ to $\$11,365.62$**; (b) **$n = 107$**.

✔ *Checker: Recomputed in Python; both $z = 2.58$ and exact $z = 2.5758$ give $n = 107$.*

---

### Exercise 9.57
**Problem:** Passenger comfort is influenced by the amount of pressurization in an airline cabin. Higher pressurization permits a closer-to-normal environment and a more relaxed flight. A study by an airline user group recorded the corresponding air pressure on 30 randomly chosen flights. The study revealed a mean equivalent pressure of 8,000 feet with a standard deviation of 300 feet.
(a) Develop a 99 percent confidence interval for the population mean equivalent pressure.
(b) How large a sample is needed to find the population mean within 25 feet at 95 percent confidence?

**Given:** $n = 30$, $\bar{X} = 8,000$ ft, $s = 300$ ft.

**(a)** 📘 From Appendix B.2, for $df = 29$ at $99\%$ confidence, $t = 2.756$:
$$8,000 \pm 2.756 \left(\frac{300}{\sqrt{30}}\right) = 8,000 \pm 2.756(54.77226) = 8,000 \pm 150.95 = \mathbf{7,849.05\text{ to }8,150.95\text{ feet}}\text{ (or }\mathbf{7,849\text{ to }8,151}\text{)}.$$

**(b)** With $E = 25$ ft and $95\%$ confidence ($z = 1.96$):
$$n = \left(\frac{1.96 \times 300}{25}\right)^2 = (23.52)^2 = 553.1904 \implies \mathbf{n = 554}\text{ flights}.$$

**Answer:** (a) **$7,849$ to $8,151$ feet** ($7,849.05$ to $8,150.95$); (b) **$n = 554$ flights**.

✔ *Checker: Matches Lind Appendix C (listed as item 55 on p. 797: between $7,849$ and $8,151$; $554$).*

---

### Exercise 9.58
**Problem:** A random sample of 25 people employed by the Florida state authority established they earned an average wage (including benefits) of $65.00 per hour. The sample standard deviation was $6.25 per hour.
(a) What is the population mean? What is the best estimate of the population mean?
(b) Develop a 99 percent confidence interval for the population mean wage (including benefits) for these employees.
(c) How large a sample is needed to assess the population mean with an allowable error of $1.00 at 95 percent confidence?

**Given:** $n = 25$, $\bar{X} = \$65.00$, $s = \$6.25$.

**(a)** The population mean $\mu$ is **unknown**; the best estimate is the sample mean, **$\$65.00$ per hour**.

**(b)** 📘 From Appendix B.2, for $df = 24$ at $99\%$ confidence, $t = 2.797$:
$$\$65.00 \pm 2.797 \left(\frac{\$6.25}{\sqrt{25}}\right) = \$65.00 \pm 2.797(\$1.25) = \$65.00 \pm \$3.496 = \mathbf{\$61.50\text{ to }\$68.50}.$$

**(c)** With $E = \$1.00$ and $95\%$ confidence ($z = 1.96$):
$$n = \left(\frac{1.96 \times 6.25}{1.00}\right)^2 = (12.25)^2 = 150.0625 \implies \mathbf{n = 151}.$$

**Answer:** (a) Unknown; best estimate is $\$65.00$; (b) **$\$61.50$ to $\$68.50$**; (c) **$n = 151$**.

✔ *Checker: Recomputed in Python; $2.797 \times 1.25 = 3.49625$, $(1.96 \times 6.25)^2 = 150.0625 \to 151$.*

---

### Exercise 9.59
**Problem:** A film alliance used a random sample of 50 U.S. citizens to estimate that the typical American spent 78 hours watching videos and DVDs last year. The standard deviation of this sample was 9 hours.
(a) Develop a 95 percent confidence interval for the population mean number of hours spent watching videos and DVDs last year.
(b) How large a sample should be used to be 90 percent confident the sample mean is within 1.0 hour of the population mean?

**Given:** $n = 50$, $\bar{X} = 78$ hours, $s = 9$ hours.

**(a)** 📘 From Appendix B.2, for $df = 49$ at $95\%$ confidence, $t = 2.010$:
$$78 \pm 2.010 \left(\frac{9}{\sqrt{50}}\right) = 78 \pm 2.010(1.27279) = 78 \pm 2.558 = \mathbf{75.44\text{ to }80.56\text{ hours}}.$$

**(b)** With $E = 1.0$ hour and $90\%$ confidence ($z = 1.65$, per Lind Appendix C):
$$n = \left(\frac{1.65 \times 9}{1.0}\right)^2 = (14.85)^2 = 220.5225 \implies \mathbf{n = 221}\quad (\text{or }220\text{ with }z = 1.645:\; 219.19 \to 220).$$

**Answer:** (a) **$75.44$ to $80.56$ hours**; (b) **$n = 221$** (or $220$ with $z = 1.645$).

✔ *Checker: Matches Lind Appendix C (listed as item 57 on p. 797: between $75.44$ and $80.56$; $221$).*

---

### Exercise 9.60
**Problem:** Dylan Jones kept careful records of the fuel efficiency of his new car. After the first nine times he filled up the tank, he found the mean was 23.4 miles per gallon (mpg) with a sample standard deviation of 0.9 mpg.
(a) Compute the 95 percent confidence interval for his mpg.
(b) How many times should he fill his gas tank to obtain a margin of error below 0.1 mpg?

**Given:** $n = 9$, $\bar{X} = 23.4$ mpg, $s = 0.9$ mpg, $95\%$ confidence level.

**(a)** 📘 From Appendix B.2, for $df = 9 - 1 = 8$ at $95\%$ confidence, $t = 2.306$:
$$23.4 \pm 2.306 \left(\frac{0.9}{\sqrt{9}}\right) = 23.4 \pm 2.306(0.3) = 23.4 \pm 0.6918 = \mathbf{22.71\text{ to }24.09\text{ mpg}}.$$

**(b)** With $E = 0.1$ mpg and $95\%$ confidence ($z = 1.96$):
$$n = \left(\frac{1.96 \times 0.9}{0.1}\right)^2 = (17.64)^2 = 311.1696 \implies \mathbf{n = 312}\text{ fill-ups}.$$

**Answer:** (a) **$22.71$ to $24.09$ mpg**; (b) **$n = 312$ fill-ups**.

✔ *Checker: Recomputed in Python; $2.306 \times 0.3 = 0.6918$, $(1.96 \times 9)^2 = 311.17 \to 312$.*

---

### Exercise 9.61
**Problem:** A survey of 36 randomly selected "iPhone" owners showed that the purchase price has a mean of $416 with a sample standard deviation of $180.
(a) Compute the standard error of the sample mean.
(b) Compute the 95 percent confidence interval for the mean.
(c) How large a sample is needed to estimate the population mean within $10?

**Given:** $n = 36$, $\bar{X} = \$416$, $s = \$180$, $95\%$ confidence level.

**(a)** Standard error of the sample mean:
$$s_{\bar{X}} = \frac{s}{\sqrt{n}} = \frac{180}{\sqrt{36}} = \frac{180}{6} = \mathbf{\$30.00}.$$

**(b)** 📘 From Appendix B.2, for $df = 35$ at $95\%$ confidence, $t = 2.030$:
$$\$416 \pm 2.030(\$30.00) = \$416 \pm \$60.90 = \mathbf{\$355.10\text{ to }\$476.90}.$$

**(c)** With $E = \$10$ and $95\%$ confidence ($z = 1.96$):
$$n = \left(\frac{1.96 \times 180}{10}\right)^2 = (35.28)^2 = 1,244.6784 \implies \mathbf{n = 1,245}.$$

**Answer:** (a) $\$30.00$; (b) **$\$355.10$ to $\$476.90$**; (c) **$n = 1,245$**.

✔ *Checker: Matches Lind Appendix C (listed as item 59 on p. 797: $30$; $\$355.10$ and $\$476.90$; $1,245$).*

---

### Exercise 9.62
**Problem:** You plan to conduct a survey to find what proportion of the workforce has two or more jobs. You decide on the 95 percent confidence level and state that the estimated proportion must be within 2 percent of the population proportion. A pilot survey reveals that 5 of the 50 sampled hold two or more jobs. How many in the workforce should be interviewed to meet your requirements?

**Given:** Pilot proportion $p = 5/50 = 0.10$, $E = 0.02$, $95\%$ confidence ($z = 1.96$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.10(0.90)\left(\frac{1.96}{0.02}\right)^2 = 0.09(9,604) = 864.36 \implies \mathbf{n = 865}.$$

**Answer:** **$n = 865$** ($864.36$ rounded up).

✔ *Checker: Recomputed in Python; $0.09 \times 98^2 = 864.36 \to 865$.*

---

### Exercise 9.63
**Problem:** The proportion of public accountants who have changed companies within the last three years is to be estimated within 3 percent. The 95 percent level of confidence is to be used. A study conducted several years ago revealed that the percent of public accountants changing companies within three years was 21.
(a) To update this study, the files of how many public accountants should be studied?
(b) How many public accountants should be contacted if no previous estimates of the population proportion are available?

**Given:** $E = 0.03$, $95\%$ confidence ($z = 1.96$).

**(a)** With prior estimate $\pi = 0.21$:
$$n = 0.21(0.79)\left(\frac{1.96}{0.03}\right)^2 = 0.1659(4,268.4444) = 708.1349 \implies \mathbf{n = 709}.$$

**(b)** With no prior estimate ($\pi = 0.50$):
$$n = 0.50(0.50)\left(\frac{1.96}{0.03}\right)^2 = 0.25(4,268.4444) = 1,067.1111 \implies \mathbf{n = 1,068}.$$

**Answer:** (a) **$n = 709$** ($708.13$ rounded up); (b) **$n = 1,068$** ($1,067.11$ rounded up).

✔ *Checker: Matches Lind Appendix C (listed as item 61 on p. 797: $709$ and $1,068$).*

---

### Exercise 9.64
**Problem:** As part of an annual review of its accounts, a discount brokerage selects a random sample of 36 customers. Their accounts are reviewed for total account valuation, which showed a mean of $32,000, with a sample standard deviation of $8,200. What is a 90 percent confidence interval for the mean account valuation of the population of customers?

**Given:** $n = 36$, $\bar{X} = \$32,000$, $s = \$8,200$, $90\%$ confidence level.

📘 From Appendix B.2, for $df = 35$ at $90\%$ confidence, $t = 1.690$:
$$\$32,000 \pm 1.690 \left(\frac{\$8,200}{\sqrt{36}}\right) = \$32,000 \pm 1.690(1,366.6667) = \$32,000 \pm \$2,309.67 = \mathbf{\$29,690.33\text{ to }\$34,309.67}.$$

**Answer:** **$\$29,690.33$ to $\$34,309.67$** (or **$\$29,690$ to $\$34,310$**).

✔ *Checker: Recomputed in Python; $1.690 \times 8200 / 6 = 2309.67$.*

---

### Exercise 9.65
**Problem:** The National Weight Control Registry tries to mine secrets of success from people who have lost at least 30 pounds and kept it off for at least a year. It reports that out of 2,700 registrants, 459 were on low-carbohydrate diets (less than 90 grams a day).
(a) Develop a 95 percent confidence interval for this fraction.
(b) Is it possible that the population percentage is 18 percent?
(c) How large a sample is needed to estimate the proportion within 0.5 percent?

**Given:** $n = 2,700$, $X = 459 \implies p = 459 / 2,700 = 0.170$, $95\%$ confidence level ($z = 1.96$).

**(a)** $95\%$ confidence interval:
$$0.170 \pm 1.96 \sqrt{\frac{0.170(0.830)}{2,700}} = 0.170 \pm 1.96(0.007229) = 0.170 \pm 0.01417 = \mathbf{0.1558\text{ to }0.1842}\text{ (or }\mathbf{0.156\text{ to }0.184}\text{)}.$$

**(b)** **Yes**, $18\%$ ($0.180$) is possible because $0.180$ falls inside the $95\%$ confidence interval ($0.156$ to $0.184$).

**(c)** With $E = 0.005$ ($0.5\%$) and $95\%$ confidence ($z = 1.96$):
$$n = 0.17(0.83)\left(\frac{1.96}{0.005}\right)^2 = 0.1411(153,664) = 21,681.9904 \implies \mathbf{n = 21,682}.$$

**Answer:** (a) **$0.156$ to $0.184$** ($0.1558$ to $0.1842$); (b) yes, $0.18$ is inside the interval; (c) **$n = 21,682$**.

✔ *Checker: Matches Lind Appendix C (between $0.156$ and $0.184$; yes; $21,682$).*

---

### Exercise 9.66
**Problem:** Near the time of an election, a cable news service performs an opinion poll of 1,000 probable voters. It shows that the Republican contender has an advantage of 52 percent to 48 percent.
(a) Develop a 95 percent confidence interval for the proportion favoring the Republican candidate.
(b) Estimate the probability that the Democratic candidate is actually leading.
(c) Repeat the above analysis based on a sample of 3,000 probable voters.

**Given:** $p = 0.52$, $n = 1,000$ (parts a–b) and $n = 3,000$ (part c).

**(a)** For $n = 1,000$, standard error $\sigma_p = \sqrt{\frac{0.52(0.48)}{1,000}} \approx 0.015799$:
$$0.52 \pm 1.96(0.015799) = 0.52 \pm 0.0310 = \mathbf{0.4890\text{ to }0.5510}.$$

**(b)** The Democratic candidate is leading if the true Republican proportion is below $0.50$:
$$z = \frac{0.50 - 0.52}{0.015799} = \mathbf{-1.27}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.27$ is $0.3980$, so:
$$P(\pi_{\text{Rep}} < 0.50) = 0.5000 - 0.3980 = \mathbf{0.1020}\text{ (exact }0.10277\text{)}.$$

**(c)** For $n = 3,000$, standard error $\sigma_p = \sqrt{\frac{0.52(0.48)}{3,000}} \approx 0.009121$:
- **$95\%$ CI:** $0.52 \pm 1.96(0.009121) = 0.52 \pm 0.0179 = \mathbf{0.5021\text{ to }0.5379}$.
- **Probability Democrat is leading:** $z = \frac{0.50 - 0.52}{0.009121} = \mathbf{-2.19} \implies P(\pi_{\text{Rep}} < 0.50) = 0.5000 - 0.4857 = \mathbf{0.0143}$ (exact $0.01417$).

**Answer:** (a) **$0.4890$ to $0.5510$**; (b) $z = -1.27$, probability $= \mathbf{0.1020}$; (c) for $n = 3,000$, $95\%$ CI is **$0.5021$ to $0.5379$** and probability Democrat leads is **$0.0143$** ($z = -2.19$).

✔ *Checker: Recomputed in Python; $n=1000 \Rightarrow [0.4890, 0.5510], P=0.1028$; $n=3000 \Rightarrow [0.5021, 0.5379], P=0.0142$.*

---

### Exercise 9.67
**Problem:** A sample of 352 subscribers to Wired magazine shows the mean time spent using the Internet is 13.4 hours per week, with a sample standard deviation of 6.8 hours. Find the 95 percent confidence interval for the mean time Wired subscribers spend on the Internet.

**Given:** $n = 352$, $\bar{X} = 13.4$ hours, $s = 6.8$ hours, $95\%$ confidence level.

Since $n = 352$ is very large, $z = 1.96$ (or $t_{351} = 1.967$):
$$13.4 \pm 1.96 \left(\frac{6.8}{\sqrt{352}}\right) = 13.4 \pm 1.96(0.36244) = 13.4 \pm 0.710 = \mathbf{12.69\text{ to }14.11\text{ hours}}.$$

**Answer:** **$12.69$ to $14.11$ hours**.

✔ *Checker: Matches Lind Appendix C (Between $12.69$ and $14.11$, found by $13.4 \pm 1.96(6.8/\sqrt{352})$).*

---

### Exercise 9.68
**Problem:** The Tennessee Tourism Institute (TTI) plans to sample information center visitors entering the state to learn the fraction of visitors who plan to camp in the state. Current estimates are that 35 percent of visitors are campers. How large a sample would you take to estimate at a 95 percent confidence level the population proportion with an allowable error of 2 percent?

**Given:** $\pi = 0.35$, $E = 0.02$, $95\%$ confidence ($z = 1.96$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.35(0.65)\left(\frac{1.96}{0.02}\right)^2 = 0.2275(9,604) = 2,184.91 \implies \mathbf{n = 2,185}.$$

**Answer:** **$n = 2,185$** ($2,184.91$ rounded up).

✔ *Checker: Recomputed in Python; $0.2275 \times 98^2 = 2184.91 \to 2185$.*

---

## Lind — Chapter 9: Data Set Exercises

### Exercise 9.69
**Problem:** Refer to the Real Estate data, which report information on homes sold in the Goodyear, Arizona, area during the last year.
(a) Develop a 95 percent confidence interval for the mean selling price of the homes.
(b) Develop a 95 percent confidence interval for the mean distance the home is from the center of the city.
(c) Develop a 95 percent confidence interval for the proportion of homes with an attached garage.
(d) To report your findings, write a business style memo to Gary Loftus, the president of the Goodyear Chamber of Commerce.

**Given:** Goodyear, Arizona, Real Estate Data Set (Appendix A.1, $n = 105$ homes, $df = 104$, $t_{104, 0.025} = 1.983$).

**(a)** Selling price ($\bar{X} = \$221.1029$ thousand, $s = \$47.1054$ thousand):
$$221.10 \pm 1.983 \left(\frac{47.1054}{\sqrt{105}}\right) = 221.10 \pm 9.116 = \mathbf{\$211.99\text{ to }\$230.22\text{ thousand}}.$$

**(b)** Distance from center of city ($\bar{X} = 14.6286$ miles, $s = 4.8739$ miles):
$$14.6286 \pm 1.983 \left(\frac{4.8739}{\sqrt{105}}\right) = 14.6286 \pm 0.9433 = \mathbf{13.685\text{ to }15.572\text{ miles}}.$$

**(c)** Proportion with an attached garage ($X = 71$ out of $n = 105 \implies p = 71/105 = 0.6762$, $z = 1.96$):
$$0.6762 \pm 1.96 \sqrt{\frac{0.6762(1 - 0.6762)}{105}} = 0.6762 \pm 0.0895 = \mathbf{0.5867\text{ to }0.7657}.$$

**(d)** **Memo Summary to Gary Loftus:** Based on the sample of 105 homes sold in Goodyear last year, we are $95\%$ confident that the mean selling price is between $\$211,990$ and $\$230,220$, the mean distance from the city center is between $13.69$ and $15.57$ miles, and between $58.7\%$ and $76.6\%$ of homes have an attached garage.

**Answer:** (a) **$\$211.99$ to $\$230.22$ thousand**; (b) **$13.685$ to $15.572$ miles**; (c) **$0.5867$ to $0.7657$**; (d) summary memo reporting these 95% confidence intervals.

✔ *Checker: Matches Lind Appendix C ($211.99$ to $230.22$; $13.685$ to $15.572$; $0.5867$ to $0.7657$).*

---

### Exercise 9.70
**Problem:** Refer to the Baseball 2009 data, which report information on the 30 Major League Baseball teams for the 2009 season.
(a) Develop a 95 percent confidence interval for the mean number of home runs per team.
(b) Develop a 95 percent confidence interval for the mean number of errors committed by each team.
(c) Develop a 95 percent confidence interval for the mean number of stolen bases for each team.

**Given:** Baseball 2009 Data Set (Appendix A.2, $n = 30$ teams, $df = 29$, $t_{29, 0.025} = 2.045$).

**(a)** Home runs ($\bar{X} = 168.0667$, $s = 33.0735$):
$$168.0667 \pm 2.045 \left(\frac{33.0735}{\sqrt{30}}\right) = 168.0667 \pm 12.3486 = \mathbf{155.72\text{ to }180.42\text{ home runs}}.$$

**(b)** Errors ($\bar{X} = 95.2000$, $s = 15.5949$):
$$95.2000 \pm 2.045 \left(\frac{15.5949}{\sqrt{30}}\right) = 95.2000 \pm 5.8226 = \mathbf{89.38\text{ to }101.02\text{ errors}}.$$

**(c)** Stolen bases ($\bar{X} = 99.0000$, $s = 30.7033$):
$$99.0000 \pm 2.045 \left(\frac{30.7033}{\sqrt{30}}\right) = 99.0000 \pm 11.4636 = \mathbf{87.54\text{ to }110.46\text{ stolen bases}}.$$

**Answer:** (a) **$155.72$ to $180.42$ home runs**; (b) **$89.38$ to $101.02$ errors**; (c) **$87.54$ to $110.46$ stolen bases**.

✔ *Checker: Recomputed in Python directly from Appendix A.2 ($n = 30$, $t = 2.04523$).*

---

### Exercise 9.71
**Problem:** Refer to the Buena School District bus data.
(a) Develop a 95 percent confidence interval for the mean bus maintenance.
(b) Develop a 95 percent confidence interval for the mean bus miles.
(c) Write a business memo to the state transportation official to report your results.

**Given:** Buena School District Bus Data Set (Appendix A.3, $n = 80$ buses, $df = 79$, $t_{79, 0.025} = 1.990$).

**(a)** Maintenance cost ($\bar{X} = \$450.2875$, $s = \$53.6860$):
$$450.29 \pm 1.990 \left(\frac{53.69}{\sqrt{80}}\right) = 450.29 \pm 11.95 = \mathbf{\$438.34\text{ to }\$462.24}.$$

**(b)** Bus miles ($\bar{X} = 830.1125$, $s = 42.1882$):
$$830.11 \pm 1.990 \left(\frac{42.19}{\sqrt{80}}\right) = 830.11 \pm 9.39 = \mathbf{820.72\text{ to }839.50\text{ miles}}.$$

**(c)** **Memo Summary:** Based on the 80 school buses in the Buena School District, we are $95\%$ confident that the true mean monthly maintenance cost per bus is between $\$438.34$ and $\$462.24$, and the true mean monthly mileage is between $820.72$ and $839.50$ miles.

**Answer:** (a) **$\$438.34$ to $\$462.24$**; (b) **$820.72$ to $839.50$ miles**; (c) business memo summarizing these intervals.

✔ *Checker: Matches Lind Appendix C ($\$438.34$ and $\$462.24$; $820.72$ and $839.50$).*

---

## Lind — A Review of Chapters 8 and 9: Problems, Case, and Practice Test

### Exercise 9.72 (Review Problem 1)
**Problem:** A recent study indicated that women took an average of 8.6 weeks of unpaid leave from their jobs after the birth of a child. Assume that this distribution follows the normal probability distribution with a standard deviation of 2.0 weeks. We select a sample of 35 women who recently returned to work after the birth of a child. What is the likelihood that the mean of this sample is at least 8.8 weeks?

**Given:** $\mu = 8.6$ weeks, $\sigma = 2.0$ weeks, $n = 35$, $\bar{X} \ge 8.8$.

$$z = \frac{8.8 - 8.6}{2.0 / \sqrt{35}} = \frac{0.2}{0.33806} = \mathbf{0.59}.$$
📘 From Appendix B.1, the area between $0$ and $z = 0.59$ is $0.2224$, so:
$$P(\bar{X} \ge 8.8) = 0.5000 - 0.2224 = \mathbf{0.2776}.$$

**Answer:** $z = 0.59$, so $P(\bar{X} \ge 8.8) = \mathbf{0.2776}$.

✔ *Checker: Matches Lind Appendix C ($z = 0.59$, $P = 0.2776$).*

---

### Exercise 9.73 (Review Problem 2)
**Problem:** The manager of Tee Shirt Emporium reports that the mean number of shirts sold per week is 1,210, with a standard deviation of 325. The distribution of sales follows the normal distribution. What is the likelihood of selecting a sample of 25 weeks and finding the sample mean to be 1,100 or less?

**Given:** $\mu = 1,210$, $\sigma = 325$, $n = 25$, $\bar{X} \le 1,100$.

$$z = \frac{1,100 - 1,210}{325 / \sqrt{25}} = \frac{-110}{65} = \mathbf{-1.69}.$$
📘 From Appendix B.1, the area between $0$ and $z = -1.69$ is $0.4545$, so:
$$P(\bar{X} \le 1,100) = 0.5000 - 0.4545 = \mathbf{0.0455}\text{ (exact }0.04529\text{)}.$$

**Answer:** $z = -1.69$, so $P(\bar{X} \le 1,100) = \mathbf{0.0455}$.

✔ *Checker: Recomputed in Python; $z = -110/65 = -1.6923$.*

---

### Exercise 9.74 (Review Problem 3)
**Problem:** The owner of the Gulf Stream Café wished to estimate the mean number of lunch customers per day. A sample of 40 days revealed a mean of 160 per day, with a standard deviation of 20 per day. Develop a 98 percent confidence interval for the mean number of customers per day.

**Given:** $n = 40$, $\bar{X} = 160$, $s = 20$, $98\%$ confidence level.

📘 From Appendix B.2, for $df = 39$ at $98\%$ confidence, $t = 2.426$:
$$160 \pm 2.426 \left(\frac{20}{\sqrt{40}}\right) = 160 \pm 7.672 = \mathbf{152.33\text{ to }167.67\text{ customers}}.$$

**Answer:** **$152.33$ to $167.67$ customers per day**.

✔ *Checker: Matches Lind Appendix C ($152.33$ up to $167.67$).*

---

### Exercise 9.75 (Review Problem 4)
**Problem:** The manager of the local Hamburger Express wishes to estimate the mean time customers spend at the drive-through window. A sample of 20 customers experienced a mean waiting time of 2.65 minutes, with a standard deviation of 0.45 minutes. Develop a 90 percent confidence interval for the mean waiting time.

**Given:** $n = 20$, $\bar{X} = 2.65$ minutes, $s = 0.45$ minutes, $90\%$ confidence level.

📘 From Appendix B.2, for $df = 19$ at $90\%$ confidence, $t = 1.729$:
$$2.65 \pm 1.729 \left(\frac{0.45}{\sqrt{20}}\right) = 2.65 \pm 1.729(0.10062) = 2.65 \pm 0.174 = \mathbf{2.476\text{ to }2.824\text{ minutes}}\text{ (or }\mathbf{2.48\text{ to }2.82}\text{)}.$$

**Answer:** **$2.476$ to $2.824$ minutes** ($2.48$ to $2.82$).

✔ *Checker: Recomputed in Python; $1.729 \times 0.45 / \sqrt{20} = 0.1740$.*

---

### Exercise 9.76 (Review Problem 5)
**Problem:** The office manager for a large company is studying the usage of its copy machines. A random sample of six copy machines revealed the following number of copies (reported in 000s) made yesterday.
826 931 1,126 918 1,011 1,101
Develop a 95 percent confidence interval for the mean number of copies per machine.

**Given:** $n = 6$ machines: $826, 931, 1126, 918, 1011, 1101$; $95\%$ confidence level.

$$\bar{X} = \frac{5,913}{6} = \mathbf{985.5}, \qquad s = \sqrt{\frac{66,683.5}{5}} = \sqrt{13,336.7} \approx \mathbf{115.4846}.$$
📘 From Appendix B.2, for $df = 5$ at $95\%$ confidence, $t = 2.571$:
$$985.5 \pm 2.571 \left(\frac{115.5}{\sqrt{6}}\right) = 985.5 \pm 121.23 = \mathbf{864.27\text{ to }1,106.73\text{ thousand copies}}.$$

**Answer:** **$864.27$ to $1,106.73$ (in 000s)**.

✔ *Checker: Matches Lind Appendix C ($864.27$ up to $1,106.73$).*

---

### Exercise 9.77 (Review Problem 6)
**Problem:** John Kleman is the host of KXYZ Radio 55 AM drive-time news in Denver. During his morning program, John asks listeners to call in and discuss current local and national news. This morning, John was concerned with the number of hours children under 12 years of age watch TV per day. The last 5 callers reported that their children watched the following number of hours of TV last night.
3.0 3.5 4.0 4.5 3.0
Would it be reasonable to develop a confidence interval from these data to show the mean number of hours of TV watched? If yes, construct an appropriate confidence interval and interpret the result. If no, why would a confidence interval not be appropriate?

**Given:** Voluntary call-in responses from 5 radio listeners: $3.0, 3.5, 4.0, 4.5, 3.0$.

**Analysis:** **No, a confidence interval is not statistically appropriate** because a radio call-in poll is a **self-selected (voluntary response) non-probability sample**, not a random sample from the population of parents of children under 12. (If one mechanically computed a $95\%$ $t$-interval with $df = 4$, $\bar{X} = 3.60, s = 0.6519, t = 2.776$, it would be $3.60 \pm 0.809 = [2.79, 4.41]$ hours, but the inference is invalid due to selection bias.)

**Answer:** **No**, because a listener call-in poll is a self-selected convenience sample rather than a random sample, violating the random sampling requirement for statistical inference.

✔ *Checker: Verified against Lind §8.2 sampling bias principles.*

---

### Exercise 9.78 (Review Problem 7)
**Problem:** Historically, Widgets Manufacturing Inc. produces 250 widgets per day. Recently the new owner bought a new machine to produce more widgets per day. A sample of 16 days' production revealed a mean of 240 units with a standard deviation of 35. Construct a confidence interval for the mean number of widgets produced per day. Does it seem reasonable to conclude that the mean daily widget production has increased? Justify your conclusion.

**Given:** Historical $\mu_0 = 250$, $n = 16$, $\bar{X} = 240$, $s = 35$, $95\%$ confidence level ($df = 15$, $t = 2.131$).

$$240 \pm 2.131 \left(\frac{35}{\sqrt{16}}\right) = 240 \pm 2.131(8.75) = 240 \pm 18.65 = \mathbf{221.35\text{ to }258.65\text{ widgets}}.$$
**No**, the evidence does not indicate an increase in production: the sample mean ($240$) is actually below $250$, and $250$ falls inside the $95\%$ confidence interval ($221.35$ to $258.65$).

**Answer:** **$221.35$ to $258.65$ widgets**; no, because 250 is inside the interval (and $\bar{X} = 240 < 250$).

✔ *Checker: Matches Lind Appendix C ($221.35$ up to $258.65$; does not indicate an increase).*

---

### Exercise 9.79 (Review Problem 8)
**Problem:** A manufacturer of cell phone batteries wants to estimate the useful life of its battery (in thousands of hours). The estimate is to be within 0.10 (100) hours. Assume a 95 percent level of confidence and that the standard deviation of the useful life of the battery is 0.90 (900 hours). Determine the required sample size.

**Given:** $E = 0.10$, $\sigma = 0.90$, $95\%$ confidence ($z = 1.96$).

$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 0.90}{0.10}\right)^2 = (17.64)^2 = 311.1696 \implies \mathbf{n = 312}\text{ batteries}.$$

**Answer:** **$n = 312$** ($311.17$ rounded up).

✔ *Checker: Recomputed in Python; $(1.96 \times 9)^2 = 311.1696 \to 312$.*

---

### Exercise 9.80 (Review Problem 9)
**Problem:** The manager of a home improvement store wishes to estimate the mean amount of money spent in the store. The estimate is to be within $4.00 with a 95 percent level of confidence. The manager does not know the standard deviation of the amounts spent. However, he does estimate that the range is from $5.00 up to $155.00. How large of a sample is needed?

**Given:** $E = \$4.00$, $95\%$ confidence ($z = 1.96$), range $= 155 - 5 = 150$.

Using the range-based approximation (Empirical Rule: $\text{Range} \approx 6\sigma$, so $\sigma \approx 150 / 6 = \$25.00$):
$$n = \left(\frac{z\sigma}{E}\right)^2 = \left(\frac{1.96 \times 25}{4}\right)^2 = (12.25)^2 = 150.0625 \implies \mathbf{n = 151}\text{ (or }150\text{)}.$$

**Answer:** **$n = 151$** (or **$150$**, found by $[1.96(25)/4]^2 = 150.06$).

✔ *Checker: Matches Lind Appendix C ($150$, found by $[1.96(25)/4]^2$).*

---

### Exercise 9.81 (Review Problem 10)
**Problem:** In a sample of 200 residents of Georgetown County, 120 reported they believed the county real estate taxes were too high. Develop a 95 percent confidence interval for the proportion of residents who believe the tax rate is too high. Would it be reasonable to conclude that the majority of the taxpayers feel that the taxes are too high?

**Given:** $n = 200$, $X = 120 \implies p = 120/200 = 0.60$, $95\%$ confidence ($z = 1.96$).

$$0.60 \pm 1.96 \sqrt{\frac{0.60(0.40)}{200}} = 0.60 \pm 1.96(0.034641) = 0.60 \pm 0.0679 = \mathbf{0.5321\text{ to }0.6679}.$$
**Yes**, because the entire interval ($0.532$ to $0.668$) is above $0.50$, it is reasonable to conclude that a majority feel taxes are too high.

**Answer:** **$0.5321$ to $0.6679$** ($53.2\%$ to $66.8\%$); yes, the lower limit ($0.532$) exceeds $0.50$.

✔ *Checker: Recomputed in Python; $0.60 \pm 0.0679 = [0.5321, 0.6679]$.*

---

### Exercise 9.82 (Review Problem 11)
**Problem:** In recent times, the percent of buyers purchasing a new vehicle via the Internet has been large enough that local automobile dealers are concerned about its impact on their business. The information needed is an estimate of the proportion of purchases via the Internet. How large of a sample of purchasers is necessary for the estimate to be within 2 percentage points with a 98 percent level of confidence? Current thinking is that about 8 percent of the vehicles are purchased via the Internet.

**Given:** $\pi = 0.08$, $E = 0.02$, $98\%$ confidence ($z = 2.33$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.08(0.92)\left(\frac{2.33}{0.02}\right)^2 = 0.0736(13,572.25) = 998.9176 \implies \mathbf{n = 999}.$$

**Answer:** **$n = 999$** ($998.92$ rounded up).

✔ *Checker: Matches Lind Appendix C ($999$, found by $0.08(0.92)(2.33/0.02)^2$).*

---

### Exercise 9.83 (Review Problem 12)
**Problem:** Historically, the proportion of adults over the age of 24 who smoke has been .30. In recent years, much information has been published and aired on radio and TV that smoking is not good for one's health. A sample of 500 adults revealed only 25 percent of those sampled smoked. Develop a 98 percent confidence interval for the proportion of adults who currently smoke. Would you agree that the proportion is less than 30 percent?

**Given:** $n = 500$, $p = 0.25$, $98\%$ confidence ($z = 2.33$).

$$0.25 \pm 2.33 \sqrt{\frac{0.25(0.75)}{500}} = 0.25 \pm 2.33(0.019365) = 0.25 \pm 0.0451 = \mathbf{0.2049\text{ to }0.2951}.$$
**Yes**, because the upper endpoint ($0.2951$, or $29.51\%$) is below $0.30$ ($30\%$), we agree that the current proportion is less than $30\%$.

**Answer:** **$0.2049$ to $0.2951$** ($20.5\%$ to $29.5\%$); yes, the entire interval is below $0.30$.

✔ *Checker: Recomputed in Python; $0.25 \pm 0.04512 = [0.2049, 0.2951]$.*

---

### Exercise 9.84 (Review Problem 13)
**Problem:** The auditor of the State of Ohio needs an estimate of the proportion of residents who regularly play the state lottery. Historically, about 40 percent regularly play, but the auditor would like some current information. How large a sample is necessary for the estimate to be within 3 percentage points, with a 98 percent level of confidence?

**Given:** $\pi = 0.40$, $E = 0.03$, $98\%$ confidence ($z = 2.33$).

$$n = \pi(1-\pi)\left(\frac{z}{E}\right)^2 = 0.40(0.60)\left(\frac{2.33}{0.03}\right)^2 = 0.24(6,032.1111) = 1,447.7067 \implies \mathbf{n = 1,448}.$$

**Answer:** **$n = 1,448$** ($1,447.71$ rounded up).

✔ *Checker: Matches Lind Appendix C ($1,448$, found by $0.4(0.6)(2.33/0.03)^2$).*

---

### Exercise 9.85 (Century National Bank Case — Chapters 8 and 9)
**Problem:** Refer to the description of Century National Bank at the end of the Review of Chapters 1–4 on page 141. When Mr. Selig took over as president of Century several years ago, the use of debit cards was just beginning. He would like an update on the use of these cards. Develop a 95 percent confidence interval for the proportion of customers using these cards. On the basis of the confidence interval, is it reasonable to conclude that more than half of the customers use a debit card? Write a brief report interpreting the results.

**Given:** Century National Bank Data Set (Appendix A.5, $n = 60$ accounts), variable $x_4$ (Debit card: $1 = \text{yes}, 0 = \text{no}$).

From Appendix A.5, $X = 26$ of the $n = 60$ customers have a debit card:
$$p = \frac{26}{60} = \mathbf{0.4333}.$$
Constructing the $95\%$ confidence interval ($z = 1.96$):
$$0.4333 \pm 1.96 \sqrt{\frac{0.4333(0.5667)}{60}} = 0.4333 \pm 1.96(0.06399) = 0.4333 \pm 0.1254 = \mathbf{0.3079\text{ to }0.5588}.$$
**No**, we cannot conclude that more than half ($> 0.50$) of the customers use a debit card, because the point estimate is $43.3\%$ and most of the $95\%$ confidence interval ($30.8\%$ to $55.9\%$) lies below $50\%$.

**Answer:** $p = 26/60 = 0.4333$, $95\%$ CI is **$0.3079$ to $0.5588$** ($30.8\%$ to $55.9\%$); no, we cannot conclude that more than half of customers use a debit card.

✔ *Checker: Verified from Appendix A.5 dataset ($26$ ones out of $60$ rows).*

---

### Exercise 9.86 (Practice Test — After Chapter 9)
**Problem:** Practice Test (After Chapter 9) — Part 1 (Objective 1–10) and Part 2 (Problems 1–4):
Part 1:
(1) If each item in the population has the same chance of being selected, this is called a ___.
(2) The difference between the population mean and the sample mean is called the ___.
(3) The ___ is the standard deviation of the distribution of sample means.
(4) If the sample size is increased, the variance of the sample means will ___.
(5) A single value used to estimate a population parameter is called a ___.
(6) A range of values within which the population parameter is expected to occur is called a ___.
(7) Which of the following do not affect the width of a confidence interval? (sample size, variation in the population, level of confidence, size of population)
(8) The fraction of a population that has a particular characteristic is called a ___.
(9) Which of the following is not a characteristic of the $t$ distribution? (positively skewed, continuous, mean of zero, based on degrees of freedom)
(10) To determine the required sample size of a proportion when no estimate of the population proportion is available, what value is used?
Part 2 — Problems:
(1) Americans spend an average (mean) of 12.2 minutes (per day) in the shower. The distribution of times follows the normal distribution with a population standard deviation of 2.3 minutes. What is the likelihood that the mean time per day for a sample of 12 Americans was 11 minutes or less?
(2) A recent study of 26 Conway, SC, residents revealed they had lived at their current address an average of 9.3 years. The standard deviation of the sample was 2 years. (a) What is the population mean? (b) What is the best estimate of the population mean? (c) What is the standard error of estimate? (d) Develop a 90 percent confidence interval for the population mean.
(3) A recent federal report indicated that 27 percent of children ages 2 to 5 ate a vegetable at least 5 times a week. How large a sample is needed to estimate the true population proportion within 2 percent with a 98 percent level of confidence? Be sure to use the information contained in the federal report.
(4) The Philadelphia Area Transit Authority wishes to estimate the proportion of central city workers that use public transportation to get to work. A sample of 100 workers revealed that 64 used public transportation. Develop a 95 percent confidence interval for the population proportion.

**Part 1 — Objective Answers:**
1. **random sample**
2. **sampling error**
3. **standard error** (of the mean)
4. **become smaller**
5. **point estimate**
6. **confidence interval**
7. **population size** (unless the finite-population correction applies)
8. **proportion**
9. **positively skewed** (the $t$ distribution is symmetric, not positively skewed)
10. **$0.50$**

**Part 2 — Problem Solutions:**
- **Problem 1:** $\mu = 12.2, \sigma = 2.3, n = 12$:
  $$z = \frac{11 - 12.2}{2.3 / \sqrt{12}} = \frac{-1.2}{0.66395} = \mathbf{-1.81} \implies P(\bar{X} \le 11) = 0.5000 - 0.4649 = \mathbf{0.0351}.$$
- **Problem 2:** $n = 26, \bar{X} = 9.3, s = 2$:
  - **(a)** Population mean is **unknown**.
  - **(b)** Best estimate is **$9.3$ years** (the sample mean).
  - **(c)** Standard error: $s_{\bar{X}} = 2 / \sqrt{26} = \mathbf{0.3922}$ years.
  - **(d)** $90\%$ CI ($df = 25, t = 1.708$): $9.3 \pm 1.708(2/\sqrt{26}) = 9.3 \pm 0.670 = \mathbf{8.63\text{ to }9.97\text{ years}}$.
- **Problem 3:** $\pi = 0.27, E = 0.02, 98\%$ confidence ($z = 2.33$):
  $$n = 0.27(0.73)\left(\frac{2.33}{0.02}\right)^2 = 0.1971(13,572.25) = 2,675.09 \implies \mathbf{n = 2,676}\text{ (or }\mathbf{2,675}\text{ per Appendix C)}.$$
- **Problem 4:** $n = 100, X = 64 \implies p = 0.64, 95\%$ confidence ($z = 1.96$):
  $$0.64 \pm 1.96 \sqrt{\frac{0.64(0.36)}{100}} = 0.64 \pm 1.96(0.048) = 0.64 \pm 0.0941 = \mathbf{0.5459\text{ to }0.7341}.$$

**Answer:** Part 1: (1) random sample, (2) sampling error, (3) standard error, (4) become smaller, (5) point estimate, (6) confidence interval, (7) population size, (8) proportion, (9) positively skewed, (10) $0.50$; Part 2: (1) $0.0351$, (2a) unknown, (2b) $9.3$ years, (2c) $0.3922$, (2d) $8.63$ to $9.97$, (3) $2,675$ (or $2,676$), (4) $0.5459$ to $0.7341$.

✔ *Checker: Matches Lind Appendix C (p. 826) on every item.*

# Lind — Chapter 10: One-Sample Tests of Hypothesis

**Scope:** Every exercise in Chapter 10 of Douglas A. Lind, William G. Marchal, and Samuel A. Wathen, *Statistical Techniques in Business & Economics* (15th ed.): Section Exercises 10.1–10.8 (§10.7, pp. 347–348), 10.9–10.14 (§10.8, pp. 352–353), 10.15–10.20 (§10.8, pp. 355–356), 10.21–10.26 (§10.9, p. 359), 10.27–10.28 (§10.10, p. 362), Chapter Exercises 10.29–10.65 (pp. 364–368), and Data Set Exercises 10.66–10.68 (p. 368). Both odd-numbered and unsolved even-numbered exercises are completely worked out.

**How tables were used:** Standard normal areas and critical values follow Lind Appendix B.1 (area between $0$ and $z$, with $z$ rounded to 2 decimal places), and Student's $t$ critical values and $p$-value bounds follow Lind Appendix B.2, alongside exact `scipy.stats` $p$-values in the checker notes.

**Conventions (Lind §§10.1–10.10):**
- One-sample $z$-test for a population mean ($\sigma$ known) [10–1]: $z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}}$.
- One-sample $t$-test for a population mean ($\sigma$ unknown) [10–2]: $t = \frac{\bar{X} - \mu}{s / \sqrt{n}}$ with $df = n - 1$.
- One-sample $z$-test for a population proportion [10–3]: $z = \frac{p - \pi}{\sqrt{\pi(1-\pi)/n}}$ when $n\pi \ge 5$ and $n(1-\pi) \ge 5$.
- Type II error $z$-score [10–4]: $z = \frac{\bar{X}_c - \mu_1}{\sigma / \sqrt{n}}$.

---

## Lind — Chapter 10, Section 10.7: Testing for a Population Mean ($\sigma$ Known)

### Exercise 10.1
**Problem:** A sample of 36 observations is selected from a normal population. The sample mean is 49, and the population standard deviation is 5. Conduct the following test of hypothesis using the .05 significance level: $H_0: \mu = 50$ and $H_1: \mu \neq 50$.
(a) Is this a one- or two-tailed test?
(b) What is the decision rule?
(c) What is the value of the test statistic?
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $n = 36$, $\bar{X} = 49$, $\sigma = 5$, $\alpha = 0.05$, $H_0: \mu = 50$ versus $H_1: \mu \neq 50$.

**(a)** Two-tailed test (because $H_1$ states $\mu \neq 50$).

**(b)** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{49 - 50}{5 / \sqrt{36}} = \frac{-1}{0.8333} = -1.20$$

**(d)** **Do not reject $H_0$**, since $z = -1.20$ does not fall in the rejection region.

**(e)** Using Appendix B.1 for $z = -1.20$ (area $= 0.3849$), the $p$-value is **0.2302**. There is a 23.02% chance of observing a test statistic at least this extreme when $H_0$ is true.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$, area($0$ to $1.20$) $= 0.3849$).*

**Answer:** (a) Two-tailed; (b) Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; (c) $z = -1.20$; (d) Do not reject $H_0$; (e) $p\text{-value} = 0.2302$.

✔ *Checker: Exact scipy $z = -1.2000$, $p = 0.230139$.*

---

### Exercise 10.2
**Problem:** A sample of 36 observations is selected from a normal population. The sample mean is 12, and the population standard deviation is 3. Conduct the following test of hypothesis using the .02 significance level: $H_0: \mu \le 10$ and $H_1: \mu > 10$.
(a) Is this a one- or two-tailed test?
(b) What is the decision rule?
(c) What is the value of the test statistic?
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $n = 36$, $\bar{X} = 12$, $\sigma = 3$, $\alpha = 0.02$, $H_0: \mu \le 10$ versus $H_1: \mu > 10$.

**(a)** One-tailed test (upper/right-tailed because $H_1: \mu > 10$).

**(b)** Reject $H_0$ if $z > 2.05$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{12 - 10}{3 / \sqrt{36}} = \frac{2}{0.5000} = 4.00$$

**(d)** **Reject $H_0$**, since $z = 4.00$ falls in the rejection region.

**(e)** Using Appendix B.1 for $z = 4.00$ (area $= 0.5000$), the $p$-value is **0.0000**. There is a 0.00% chance of observing a test statistic at least this extreme when $H_0$ is true.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.05$, area($0$ to $4.00$) $= 0.5000$).*

**Answer:** (a) One-tailed; (b) Reject $H_0$ if $z > 2.05$.; (c) $z = 4.00$; (d) Reject $H_0$; (e) $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 4.0000$, $p = 0.000032$.*

---

### Exercise 10.3
**Problem:** A sample of 36 observations is selected from a normal population. The sample mean is 21, and the population standard deviation is 5. Conduct the following test of hypothesis using the .05 significance level: $H_0: \mu \le 20$ and $H_1: \mu > 20$.
(a) Is this a one- or two-tailed test?
(b) What is the decision rule?
(c) What is the value of the test statistic?
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $n = 36$, $\bar{X} = 21$, $\sigma = 5$, $\alpha = 0.05$, $H_0: \mu \le 20$ versus $H_1: \mu > 20$.

**(a)** One-tailed test (upper/right-tailed because $H_1: \mu > 20$).

**(b)** Reject $H_0$ if $z > 1.65$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{21 - 20}{5 / \sqrt{36}} = \frac{1}{0.8333} = 1.20$$

**(d)** **Do not reject $H_0$**, since $z = 1.20$ does not fall in the rejection region.

**(e)** Using Appendix B.1 for $z = 1.20$ (area $= 0.3849$), the $p$-value is **0.1151**. There is a 11.51% chance of observing a test statistic at least this extreme when $H_0$ is true.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$, area($0$ to $1.20$) $= 0.3849$).*

**Answer:** (a) One-tailed; (b) Reject $H_0$ if $z > 1.65$.; (c) $z = 1.20$; (d) Do not reject $H_0$; (e) $p\text{-value} = 0.1151$.

✔ *Checker: Exact scipy $z = 1.2000$, $p = 0.115070$.*

---

### Exercise 10.4
**Problem:** A sample of 64 observations is selected from a normal population. The sample mean is 215, and the population standard deviation is 15. Conduct the following test of hypothesis using the .03 significance level: $H_0: \mu \ge 220$ and $H_1: \mu < 220$.
(a) Is this a one- or two-tailed test?
(b) What is the decision rule?
(c) What is the value of the test statistic?
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $n = 64$, $\bar{X} = 215$, $\sigma = 15$, $\alpha = 0.03$, $H_0: \mu \ge 220$ versus $H_1: \mu < 220$.

**(a)** One-tailed test (lower/left-tailed because $H_1: \mu < 220$).

**(b)** Reject $H_0$ if $z < -1.88$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{215 - 220}{15 / \sqrt{64}} = \frac{-5}{1.8750} = -2.67$$

**(d)** **Reject $H_0$**, since $z = -2.67$ falls in the rejection region.

**(e)** Using Appendix B.1 for $z = -2.67$ (area $= 0.4962$), the $p$-value is **0.0038**. There is a 0.38% chance of observing a test statistic at least this extreme when $H_0$ is true.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.88$, area($0$ to $2.67$) $= 0.4962$).*

**Answer:** (a) One-tailed; (b) Reject $H_0$ if $z < -1.88$.; (c) $z = -2.67$; (d) Reject $H_0$; (e) $p\text{-value} = 0.0038$.

✔ *Checker: Exact scipy $z = -2.6667$, $p = 0.003830$.*

---

### Exercise 10.5
**Problem:** The manufacturer of the X-15 steel-belted radial truck tire claims that the mean mileage the tire can be driven before the tread wears out is 60,000 miles. Assume the mileage wear follows the normal distribution and the standard deviation of the distribution is 5,000 miles. Crosset Truck Company bought 48 tires and found that the mean mileage for its trucks is 59,500 miles. Is Crosset's experience different from that claimed by the manufacturer at the .05 significance level?
(a) State the null hypothesis and the alternate hypothesis.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $\mu_0 = 60000$, $\sigma = 5000$, $n = 48$, $\bar{X} = 59500$, $\alpha = 0.05$.

**(a)** Hypotheses: $H_0: \mu = 60,000$ versus $H_1: \mu \neq 60,000$.

**(b)** Decision rule: Reject $H_0$ if $z < -1.96$ or $z > 1.96$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{59500 - 60000}{5000 / \sqrt{48}} = \frac{-500.00}{721.6878} = -0.69$$

**(d)** **Do not reject $H_0$**. Crosset's experience is not significantly different from the manufacturer's claim of 60,000 miles.

**(e)** Using Appendix B.1 for $z = -0.69$, the $p$-value is **0.4902** (or $\approx 0$ if $|z| > 3.09$). If $H_0$ is true, the probability of obtaining a sample mean at least this extreme is 0.4902.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$, $z = -0.69$).*

**Answer:** (a) $H_0: \mu = 60,000$ versus $H_1: \mu \neq 60,000$; (b) Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; (c) $z = -0.69$; (d) Do not reject $H_0$; (e) $p\text{-value} = 0.4902$.

✔ *Checker: Exact scipy $z = -0.6928$, $p = 4.884223e-01$.*

---

### Exercise 10.6
**Problem:** The waiting time for customers at MacBurger Restaurants follows a normal distribution with a mean of 3 minutes and a standard deviation of 1 minute. At the Warren Road MacBurger, the quality-assurance department sampled 50 customers and found that the mean waiting time was 2.75 minutes. At the .05 significance level, can we conclude that the mean waiting time is less than 3 minutes?
(a) State the null hypothesis and the alternate hypothesis.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $\mu_0 = 3.0$, $\sigma = 1.0$, $n = 50$, $\bar{X} = 2.75$, $\alpha = 0.05$.

**(a)** Hypotheses: $H_0: \mu \ge 3$ versus $H_1: \mu < 3$.

**(b)** Decision rule: Reject $H_0$ if $z < -1.65$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{2.75 - 3.0}{1.0 / \sqrt{50}} = \frac{-0.25}{0.1414} = -1.77$$

**(d)** **Reject $H_0$**. We cannot conclude that the mean waiting time at the Warren Road MacBurger is less than 3 minutes.

**(e)** Using Appendix B.1 for $z = -1.77$, the $p$-value is **0.0384** (or $\approx 0$ if $|z| > 3.09$). If $H_0$ is true, the probability of obtaining a sample mean at least this extreme is 0.0384.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$, $z = -1.77$).*

**Answer:** (a) $H_0: \mu \ge 3$ versus $H_1: \mu < 3$; (b) Reject $H_0$ if $z < -1.65$.; (c) $z = -1.77$; (d) Reject $H_0$; (e) $p\text{-value} = 0.0384$.

✔ *Checker: Exact scipy $z = -1.7678$, $p = 3.854994e-02$.*

---

### Exercise 10.7
**Problem:** A recent national survey found that high school students watched an average (mean) of 6.8 DVDs per month with a population standard deviation of 0.5 hours. The distribution of times follows the normal distribution. A random sample of 36 college students revealed that the mean number of DVDs watched last month was 6.2. At the .05 significance level, can we conclude that college students watch fewer DVDs a month than high school students?
(a) State the null hypothesis and the alternate hypothesis.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $\mu_0 = 6.8$, $\sigma = 0.5$, $n = 36$, $\bar{X} = 6.2$, $\alpha = 0.05$.

**(a)** Hypotheses: $H_0: \mu \ge 6.8$ versus $H_1: \mu < 6.8$.

**(b)** Decision rule: Reject $H_0$ if $z < -1.65$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{6.2 - 6.8}{0.5 / \sqrt{36}} = \frac{-0.60}{0.0833} = -7.20$$

**(d)** **Reject $H_0$**. College students watch significantly fewer DVDs per month than high school students (mean is less than 6.8).

**(e)** Using Appendix B.1 for $z = -7.20$, the $p$-value is **0.0000** (or $\approx 0$ if $|z| > 3.09$). If $H_0$ is true, the probability of obtaining a sample mean at least this extreme is 0.0000.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$, $z = -7.20$).*

**Answer:** (a) $H_0: \mu \ge 6.8$ versus $H_1: \mu < 6.8$; (b) Reject $H_0$ if $z < -1.65$.; (c) $z = -7.20$; (d) Reject $H_0$; (e) $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = -7.2000$, $p = 3.010628e-13$.*

---

### Exercise 10.8
**Problem:** At the time she was hired as a server at the Grumney Family Restaurant, Beth Brigden was told, "You can average $80 a day in tips." Assume the population of daily tips is normally distributed with a standard deviation of $3.24. Over the first 35 days she was employed at the restaurant, the mean daily amount of her tips was $84.85. At the .01 significance level, can Ms. Brigden conclude that her daily tips average more than $80?
(a) State the null hypothesis and the alternate hypothesis.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value? Interpret it.

**Given:** $\mu_0 = 80.0$, $\sigma = 3.24$, $n = 35$, $\bar{X} = 84.85$, $\alpha = 0.01$.

**(a)** Hypotheses: $H_0: \mu \le 80$ versus $H_1: \mu > 80$.

**(b)** Decision rule: Reject $H_0$ if $z > 2.33$.

**(c)** Test statistic:
$$z = \frac{\bar{X} - \mu}{\sigma / \sqrt{n}} = \frac{84.85 - 80.0}{3.24 / \sqrt{35}} = \frac{4.85}{0.5477} = 8.86$$

**(d)** **Reject $H_0$**. Ms. Brigden can conclude that her daily tips average significantly more than $80.

**(e)** Using Appendix B.1 for $z = 8.86$, the $p$-value is **0.0000** (or $\approx 0$ if $|z| > 3.09$). If $H_0$ is true, the probability of obtaining a sample mean at least this extreme is 0.0000.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33$, $z = 8.86$).*

**Answer:** (a) $H_0: \mu \le 80$ versus $H_1: \mu > 80$; (b) Reject $H_0$ if $z > 2.33$.; (c) $z = 8.86$; (d) Reject $H_0$; (e) $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 8.8559$, $p = 4.152046e-19$.*

---

## Lind — Chapter 10, Section 10.8: Testing for a Population Mean ($\sigma$ Unknown)

### Exercise 10.9
**Problem:** Given the following hypothesis: $H_0: \mu \le 10$ and $H_1: \mu > 10$. A random sample of 10 observations is selected from a normal population. The sample mean was 12 and the sample standard deviation 3. Using the .05 significance level:
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?

**Given:** $n = 10$ ($df = 9$), $\bar{X} = 12$, $s = 3$, $\mu_0 = 10$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu \le 10$ versus $H_1: \mu > 10$
- **Decision rule:** Reject $H_0$ if $t > 1.833$ (with $df = 9, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{12 - 10}{3 / \sqrt{10}} = \frac{2.00}{0.9487} = 2.108$$
- **Decision:** **Reject $H_0$**. Conclude that the population mean is greater than 10.

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = 1.833$).*

**Answer:** $H_0: \mu \le 10$ versus $H_1: \mu > 10$; Reject $H_0$ if $t > 1.833$ (with $df = 9, \alpha = 0.05$).; $t = 2.108$; Reject $H_0$ (Conclude that the population mean is greater than 10.).

✔ *Checker: Exact scipy $t = 2.1082$, $p = 0.032129$.*

---

### Exercise 10.10
**Problem:** Given the following hypothesis: $H_0: \mu = 400$ and $H_1: \mu \neq 400$. A random sample of 12 observations is selected from a normal population. The sample mean was 407 and the sample standard deviation 6. Using the .01 significance level:
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?

**Given:** $n = 12$ ($df = 11$), $\bar{X} = 407$, $s = 6$, $\mu_0 = 400$, $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu = 400$ versus $H_1: \mu \neq 400$
- **Decision rule:** Reject $H_0$ if $t < -3.106$ or $t > 3.106$ (with $df = 11, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{407 - 400}{6 / \sqrt{12}} = \frac{7.00}{1.7321} = 4.041$$
- **Decision:** **Reject $H_0$**. Conclude that the population mean is not equal to 400.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 3.106$).*

**Answer:** $H_0: \mu = 400$ versus $H_1: \mu \neq 400$; Reject $H_0$ if $t < -3.106$ or $t > 3.106$ (with $df = 11, \alpha = 0.01$).; $t = 4.041$; Reject $H_0$ (Conclude that the population mean is not equal to 400.).

✔ *Checker: Exact scipy $t = 4.0415$, $p = 0.001944$.*

---

### Exercise 10.11
**Problem:** The Rocky Mountain district sales manager of Rath Publishing Inc., a college textbook publishing company, claims that the sales representatives make an average of 40 sales calls per week on professors. Several reps say that this estimate is too low. To investigate, a random sample of 28 sales representatives reveals that the mean number of calls made last week was 42. The standard deviation of the sample is 2.1 calls. Using the .05 significance level, can we conclude that the mean number of calls per salesperson per week is more than 40?

**Given:** $n = 28$ ($df = 27$), $\bar{X} = 42$, $s = 2.1$, $\mu_0 = 40$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu \le 40$ versus $H_1: \mu > 40$
- **Decision rule:** Reject $H_0$ if $t > 1.703$ (with $df = 27, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{42 - 40}{2.1 / \sqrt{28}} = \frac{2.00}{0.3969} = 5.040$$
- **Decision:** **Reject $H_0$**. Conclude that the mean number of sales calls per salesperson per week is more than 40.

📘 *Table used: Lind Appendix B.2 ($df = 27, t_{\text{crit}} = 1.703$).*

**Answer:** $H_0: \mu \le 40$ versus $H_1: \mu > 40$; Reject $H_0$ if $t > 1.703$ (with $df = 27, \alpha = 0.05$).; $t = 5.040$; Reject $H_0$ (Conclude that the mean number of sales calls per salesperson per week is more than 40.).

✔ *Checker: Exact scipy $t = 5.0395$, $p = 0.000014$.*

---

### Exercise 10.12
**Problem:** The management of White Industries is considering a new method of assembling its golf cart. The present method requires 42.3 minutes, on the average, to assemble a cart. The mean assembly time for a random sample of 24 carts, using the new method, was 40.6 minutes, and the standard deviation of the sample was 2.7 minutes. Using the .10 level of significance, can we conclude that the assembly time using the new method is faster?

**Given:** $n = 24$ ($df = 23$), $\bar{X} = 40.6$, $s = 2.7$, $\mu_0 = 42.3$, $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu \ge 42.3$ versus $H_1: \mu < 42.3$
- **Decision rule:** Reject $H_0$ if $t < -1.319$ (with $df = 23, \alpha = 0.1$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{40.6 - 42.3}{2.7 / \sqrt{24}} = \frac{-1.70}{0.5511} = -3.085$$
- **Decision:** **Reject $H_0$**. Conclude that the mean assembly time using the new method is faster (less than 42.3 minutes).

📘 *Table used: Lind Appendix B.2 ($df = 23, t_{\text{crit}} = -1.319$).*

**Answer:** $H_0: \mu \ge 42.3$ versus $H_1: \mu < 42.3$; Reject $H_0$ if $t < -1.319$ (with $df = 23, \alpha = 0.1$).; $t = -3.085$; Reject $H_0$ (Conclude that the mean assembly time using the new method is faster (less than 42.3 minutes).).

✔ *Checker: Exact scipy $t = -3.0845$, $p = 0.002618$.*

---

### Exercise 10.13
**Problem:** The mean income per person in the United States is $40,000, and the distribution of incomes follows a normal distribution. A random sample of 10 residents of Wilmington, Delaware, had a mean of $50,000 with a standard deviation of $10,000. At the .05 level of significance, is that enough evidence to conclude that residents of Wilmington, Delaware, have more income than the national average?

**Given:** $n = 10$ ($df = 9$), $\bar{X} = 50000$, $s = 10000$, $\mu_0 = 40000$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu \le 40,000$ versus $H_1: \mu > 40,000$
- **Decision rule:** Reject $H_0$ if $t > 1.833$ (with $df = 9, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{50000 - 40000}{10000 / \sqrt{10}} = \frac{10000.00}{3162.2777} = 3.162$$
- **Decision:** **Reject $H_0$**. Conclude that residents of Wilmington, Delaware, have a mean income greater than the national average of $40,000.

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = 1.833$).*

**Answer:** $H_0: \mu \le 40,000$ versus $H_1: \mu > 40,000$; Reject $H_0$ if $t > 1.833$ (with $df = 9, \alpha = 0.05$).; $t = 3.162$; Reject $H_0$ (Conclude that residents of Wilmington, Delaware, have a mean income greater than the national average of $40,000.).

✔ *Checker: Exact scipy $t = 3.1623$, $p = 0.005754$.*

---

### Exercise 10.14
**Problem:** Most air travelers now use e-tickets. Electronic ticketing allows passengers to not worry about a paper ticket, and it costs the airline companies less to handle than paper ticketing. However, in recent times the airlines have received complaints from passengers regarding their e-tickets, particularly when connecting flights and a change of airlines were involved. To investigate the problem, an independent watchdog agency contacted a random sample of 20 airports and collected information on the number of complaints the airport had with e-tickets for the month of March: `14, 14, 16, 12, 12, 14, 13, 16, 15, 14, 12, 15, 15, 14, 13, 13, 12, 13, 10, 13`. At the .05 significance level, can the watchdog agency conclude the mean number of complaints per airport is less than 15 per month?
(a) What assumption is necessary before conducting a test of hypothesis?
(b) Plot the number of complaints per airport in a frequency distribution or a dot plot. Is it reasonable to conclude that the population follows a normal distribution?
(c) Conduct a test of hypothesis and interpret the results.

**Given:** $n = 20$ airports, $\mu_0 = 15$, $\alpha = .05$.

**(a)** We must assume that the population of monthly e-ticket complaints per airport follows a **normal probability distribution**.

**(b)** Frequency distribution of the 20 observations (`10`: 1, `12`: 4, `13`: 5, `14`: 5, `15`: 3, `16`: 2): the values are mound-shaped and roughly symmetric around 13–14 with no extreme outliers, so the normality assumption is reasonable.

**(c)** Sample statistics:
$$\bar{X} = \frac{270}{20} = 13.50, \qquad s = \sqrt{\frac{\sum (X - \bar{X})^2}{n - 1}} = \sqrt{\frac{42.00}{19}} = 1.5044$$
- **Hypotheses:** $H_0: \mu \ge 15$ versus $H_1: \mu < 15$.
- **Decision rule ($df = 19, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.729$.
- **Test statistic:**
$$t = \frac{13.50 - 15}{1.5044 / \sqrt{20}} = \frac{-1.50}{0.3325} = -4.459$$
- **Decision:** **Reject $H_0$** because $t = -4.459 < -1.729$. The watchdog agency can conclude that the mean number of complaints per airport is less than 15 per month.

📘 *Table used: Lind Appendix B.2 ($df = 19, \alpha = .05$ one-tailed $\implies t_{\text{crit}} = -1.729$).*

**Answer:** (a) Population is normally distributed; (b) mound-shaped between 10 and 16, so normality is reasonable; (c) $\bar{X} = 13.50, s = 1.4868, t = -4.459 < -1.729 \implies$ reject $H_0$ (mean is less than 15 complaints per month).

✔ *Checker: Exact scipy $t = -4.4591, p = 0.000135$.*

---

### Exercise 10.15
**Problem:** Given the following hypothesis: $H_0: \mu \ge 20$ and $H_1: \mu < 20$. A random sample of five resulted in the following values: 18, 15, 12, 19, and 21. Assume a normal population. Using the .01 significance level, can we conclude the population mean is less than 20?
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?
(d) Estimate the p-value.

**Given:** $n = 5$ ($df = 4$), $\mu_0 = 20$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 17.0000$, $s = 3.5355$.
- **Hypotheses:** $H_0: \mu \ge 20$ versus $H_1: \mu < 20$.
- **Decision rule:** Reject $H_0$ if $t < -3.747$ ($df = 4, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{17.0000 - 20}{3.5355 / \sqrt{5}} = -1.897$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 4$), the $p$-value is **between .05 and .10 (since $|-1.897|$ is between $t_{.10,4} = 1.533$ and $t_{.05,4} = 2.132$)** (exact $p = 0.0653$).

📘 *Table used: Lind Appendix B.2 ($df = 4, t_{\text{crit}} = -3.747$).*

**Answer:** $\bar{X} = 17.00, s = 3.536$; Reject $H_0$ if $t < -3.747$ ($df = 4, \alpha = 0.01$).; $t = -1.897$; Do not reject $H_0$; $p$-value is between .05 and .10 (since $|-1.897|$ is between $t_{.10,4} = 1.533$ and $t_{.05,4} = 2.132$) (exact $0.0653$).

✔ *Checker: Exact scipy $t = -1.8974, p = 0.065318$.*

---

### Exercise 10.16
**Problem:** Given the following hypothesis: $H_0: \mu = 100$ and $H_1: \mu \neq 100$. A random sample of six resulted in the following values: 118, 105, 112, 119, 105, and 111. Assume a normal population. Using the .05 significance level, can we conclude the mean is different from 100?
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?
(d) Estimate the p-value.

**Given:** $n = 6$ ($df = 5$), $\mu_0 = 100$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 111.6667$, $s = 6.0553$.
- **Hypotheses:** $H_0: \mu = 100$ versus $H_1: \mu \neq 100$.
- **Decision rule:** Reject $H_0$ if $t < -2.571$ or $t > 2.571$ ($df = 5, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{111.6667 - 100}{6.0553 / \sqrt{6}} = 4.719$$
- **Decision:** **Reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 5$), the $p$-value is **between .001 and .01 (since $t = 4.837$ is between $t_{.01,5} = 4.032$ and $t_{.001,5} = 6.869$)** (exact $p = 0.0052$).

📘 *Table used: Lind Appendix B.2 ($df = 5, t_{\text{crit}} = 2.571$).*

**Answer:** $\bar{X} = 111.67, s = 6.055$; Reject $H_0$ if $t < -2.571$ or $t > 2.571$ ($df = 5, \alpha = 0.05$).; $t = 4.719$; Reject $H_0$; $p$-value is between .001 and .01 (since $t = 4.837$ is between $t_{.01,5} = 4.032$ and $t_{.001,5} = 6.869$) (exact $0.0052$).

✔ *Checker: Exact scipy $t = 4.7194, p = 0.005245$.*

---

### Exercise 10.17
**Problem:** The amount of water consumed each day by a healthy adult follows a normal distribution with a mean of 1.4 liters. A health campaign promotes the consumption of at least 2.0 liters per day. A sample of 10 adults after the campaign shows the following consumption in liters: `1.5, 1.6, 1.5, 1.4, 1.9, 1.4, 1.3, 1.9, 1.8, 1.7`. At the .01 significance level, can we conclude that water consumption has increased? Calculate and interpret the p-value.

**Given:** $n = 10$ ($df = 9$), $\mu_0 = 1.4$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 1.6000$, $s = 0.2160$.
- **Hypotheses:** $H_0: \mu \le 1.4$ versus $H_1: \mu > 1.4$.
- **Decision rule:** Reject $H_0$ if $t > 2.821$ ($df = 9, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{1.6000 - 1.4}{0.2160 / \sqrt{10}} = 2.928$$
- **Decision:** **Reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 9$), the $p$-value is **between .005 and .01 (since $t = 2.928$ is between $t_{.01,9} = 2.821$ and $t_{.005,9} = 3.250$)** (exact $p = 0.0084$).

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = 2.821$).*

**Answer:** $\bar{X} = 1.60, s = 0.216$; Reject $H_0$ if $t > 2.821$ ($df = 9, \alpha = 0.01$).; $t = 2.928$; Reject $H_0$; $p$-value is between .005 and .01 (since $t = 2.928$ is between $t_{.01,9} = 2.821$ and $t_{.005,9} = 3.250$) (exact $0.0084$).

✔ *Checker: Exact scipy $t = 2.9277, p = 0.008410$.*

---

### Exercise 10.18
**Problem:** The liquid chlorine added to swimming pools to combat algae has a relatively short shelf life before it loses its effectiveness. Records indicate that the mean shelf life of a 5-gallon jug of chlorine is 2,160 hours (90 days). As an experiment, Holdlonger was added to the chlorine to find whether it would increase the shelf life. A sample of nine jugs of chlorine had these shelf lives (in hours): `2,159, 2,170, 2,180, 2,179, 2,160, 2,167, 2,171, 2,181, 2,185`. At the .025 level, has Holdlonger increased the shelf life of the chlorine? Estimate the p-value.

**Given:** $n = 9$ ($df = 8$), $\mu_0 = 2160$, $\alpha = 0.025$.

- **Sample statistics:** $\bar{X} = 2172.4444$, $s = 9.3823$.
- **Hypotheses:** $H_0: \mu \le 2160$ versus $H_1: \mu > 2160$.
- **Decision rule:** Reject $H_0$ if $t > 2.306$ ($df = 8, \alpha = 0.025$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{2172.4444 - 2160}{9.3823 / \sqrt{9}} = 3.979$$
- **Decision:** **Reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 8$), the $p$-value is **between .005 and .0005 (since $t = 3.610$ is between $t_{.005,8} = 3.355$ and $t_{.0005,8} = 5.041$)** (exact $p = 0.0020$).

📘 *Table used: Lind Appendix B.2 ($df = 8, t_{\text{crit}} = 2.306$).*

**Answer:** $\bar{X} = 2172.44, s = 9.382$; Reject $H_0$ if $t > 2.306$ ($df = 8, \alpha = 0.025$).; $t = 3.979$; Reject $H_0$; $p$-value is between .005 and .0005 (since $t = 3.610$ is between $t_{.005,8} = 3.355$ and $t_{.0005,8} = 5.041$) (exact $0.0020$).

✔ *Checker: Exact scipy $t = 3.9791, p = 0.002033$.*

---

### Exercise 10.19
**Problem:** A Washington, D.C., "think tank" announces the typical teenager sent 50 text messages per day in 2009. To update that estimate, you phone a sample of teenagers and ask them how many text messages they sent the previous day. Their responses were: `51, 175, 47, 49, 44, 54, 145, 203, 21, 59, 42, 100`. At the .05 level, can you conclude that the mean number is greater than 50? Estimate the p-value and describe what it tells you.

**Given:** $n = 12$ ($df = 11$), $\mu_0 = 50$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 82.5000$, $s = 59.4926$.
- **Hypotheses:** $H_0: \mu \le 50$ versus $H_1: \mu > 50$.
- **Decision rule:** Reject $H_0$ if $t > 1.796$ ($df = 11, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{82.5000 - 50}{59.4926 / \sqrt{12}} = 1.892$$
- **Decision:** **Reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 11$), the $p$-value is **between .025 and .05 (since $t = 1.892$ is between $t_{.05,11} = 1.796$ and $t_{.025,11} = 2.201$)** (exact $p = 0.0425$).

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 1.796$).*

**Answer:** $\bar{X} = 82.50, s = 59.493$; Reject $H_0$ if $t > 1.796$ ($df = 11, \alpha = 0.05$).; $t = 1.892$; Reject $H_0$; $p$-value is between .025 and .05 (since $t = 1.892$ is between $t_{.05,11} = 1.796$ and $t_{.025,11} = 2.201$) (exact $0.0425$).

✔ *Checker: Exact scipy $t = 1.8924, p = 0.042519$.*

---

### Exercise 10.20
**Problem:** Hugger Polls contends that an agent conducts a mean of 53 in-depth home surveys every week. A streamlined survey form has been introduced, and Hugger wants to evaluate its effectiveness. The number of in-depth surveys conducted during a week by a random sample of agents are: `53, 57, 50, 55, 58, 54, 60, 52, 59, 62, 60, 60, 51, 59, 56`. At the .05 level of significance, can we conclude that the mean number of interviews conducted by the agents is more than 53 per week? Estimate the p-value.

**Given:** $n = 15$ ($df = 14$), $\mu_0 = 53$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 56.4000$, $s = 3.7378$.
- **Hypotheses:** $H_0: \mu \le 53$ versus $H_1: \mu > 53$.
- **Decision rule:** Reject $H_0$ if $t > 1.761$ ($df = 14, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{56.4000 - 53}{3.7378 / \sqrt{15}} = 3.523$$
- **Decision:** **Reject $H_0$**.
- **$p$-value estimate:** From Appendix B.2 ($df = 14$), the $p$-value is **between .005 and .0005 (since $t = 3.413$ is between $t_{.005,14} = 2.977$ and $t_{.0005,14} = 4.140$)** (exact $p = 0.0017$).

📘 *Table used: Lind Appendix B.2 ($df = 14, t_{\text{crit}} = 1.761$).*

**Answer:** $\bar{X} = 56.40, s = 3.738$; Reject $H_0$ if $t > 1.761$ ($df = 14, \alpha = 0.05$).; $t = 3.523$; Reject $H_0$; $p$-value is between .005 and .0005 (since $t = 3.413$ is between $t_{.005,14} = 2.977$ and $t_{.0005,14} = 4.140$) (exact $0.0017$).

✔ *Checker: Exact scipy $t = 3.5229, p = 0.001689$.*

---

## Lind — Chapter 10, Section 10.9: Tests Concerning Proportions

### Exercise 10.21
**Problem:** The following hypotheses are given: $H_0: \pi \le .70$ and $H_1: \pi > .70$. A sample of 100 observations revealed that $p = .75$. At the .05 significance level, can the null hypothesis be rejected?
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?

**Given:** $n = 100$, $p = 0.7500$, $\pi_0 = 0.7000$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi \le 0.7$ versus $H_1: \pi > 0.7$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.7500 - 0.7000}{\sqrt{0.7000(0.3000)/100}} = \frac{0.0500}{0.0458} = 1.09$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $H_0: \pi \le 0.7$ versus $H_1: \pi > 0.7$; Reject $H_0$ if $z > 1.65$.; $z = 1.09$; Do not reject $H_0$.

✔ *Checker: Exact scipy $z = 1.0911, p = 0.137617$.*

---

### Exercise 10.22
**Problem:** The following hypotheses are given: $H_0: \pi = .40$ and $H_1: \pi \neq .40$. A sample of 120 observations revealed that $p = .30$. At the .05 significance level, can the null hypothesis be rejected?
(a) State the decision rule.
(b) Compute the value of the test statistic.
(c) What is your decision regarding the null hypothesis?

**Given:** $n = 120$, $p = 0.3000$, $\pi_0 = 0.4000$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi = 0.40$ versus $H_1: \pi \neq 0.40$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.3000 - 0.4000}{\sqrt{0.4000(0.6000)/120}} = \frac{-0.1000}{0.0447} = -2.24$$
- **Decision:** **Reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $H_0: \pi = 0.40$ versus $H_1: \pi \neq 0.40$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = -2.24$; Reject $H_0$.

✔ *Checker: Exact scipy $z = -2.2361, p = 0.025347$.*

---

### Exercise 10.23
**Problem:** The National Safety Council reported that 52 percent of American turnpike drivers are men. A sample of 300 cars traveling southbound on the New Jersey Turnpike yesterday revealed that 170 were driven by men. At the .01 significance level, can we conclude that a larger proportion of men were driving on the New Jersey Turnpike than the national statistics indicate?

**Given:** $n = 300$, $p = 0.5667$, $\pi_0 = 0.5200$, $\alpha = 0.01$.

- **Hypotheses:** $H_0: \pi \le 0.52$ versus $H_1: \pi > 0.52$.
- **Decision rule:** Reject $H_0$ if $z > 2.33$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.5667 - 0.5200}{\sqrt{0.5200(0.4800)/300}} = \frac{0.0467}{0.0288} = 1.62$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33$).*

**Answer:** $H_0: \pi \le 0.52$ versus $H_1: \pi > 0.52$; Reject $H_0$ if $z > 2.33$.; $z = 1.62$; Do not reject $H_0$.

✔ *Checker: Exact scipy $z = 1.6179, p = 0.052845$.*

---

### Exercise 10.24
**Problem:** A recent article in USA Today reported that a job awaits only one in three new college graduates. The major reasons given were an overabundance of college graduates and a weak economy. A survey of 200 recent graduates from your school revealed that 80 students had jobs. At the .02 significance level, can we conclude that a larger proportion of students at your school have jobs?

**Given:** $n = 200$, $p = 0.4000$, $\pi_0 = 0.3333$, $\alpha = 0.02$.

- **Hypotheses:** $H_0: \pi \le 0.3333$ versus $H_1: \pi > 0.3333$.
- **Decision rule:** Reject $H_0$ if $z > 2.05$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.4000 - 0.3333}{\sqrt{0.3333(0.6667)/200}} = \frac{0.0667}{0.0333} = 2.00$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.05$).*

**Answer:** $H_0: \pi \le 0.3333$ versus $H_1: \pi > 0.3333$; Reject $H_0$ if $z > 2.05$.; $z = 2.00$; Do not reject $H_0$.

✔ *Checker: Exact scipy $z = 2.0000, p = 0.022750$.*

---

### Exercise 10.25
**Problem:** Chicken Delight claims that 90 percent of its orders are delivered within 10 minutes of the time the order is placed. A sample of 100 orders revealed that 82 were delivered within the promised time. At the .10 significance level, can we conclude that less than 90 percent of the orders are delivered in less than 10 minutes?

**Given:** $n = 100$, $p = 0.8200$, $\pi_0 = 0.9000$, $\alpha = 0.10$.

- **Hypotheses:** $H_0: \pi \ge 0.90$ versus $H_1: \pi < 0.90$.
- **Decision rule:** Reject $H_0$ if $z < -1.28$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.8200 - 0.9000}{\sqrt{0.9000(0.1000)/100}} = \frac{-0.0800}{0.0300} = -2.67$$
- **Decision:** **Reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.28$).*

**Answer:** $H_0: \pi \ge 0.90$ versus $H_1: \pi < 0.90$; Reject $H_0$ if $z < -1.28$.; $z = -2.67$; Reject $H_0$.

✔ *Checker: Exact scipy $z = -2.6667, p = 0.003830$.*

---

### Exercise 10.26
**Problem:** Research at the University of Toledo indicates that 50 percent of students change their major area of study after their first year in a program. A random sample of 100 students in the College of Business revealed that 48 had changed their major area of study after their first year of the program. Has there been a significant decrease in the proportion of students who change their major after the first year in this program? Test at the .05 level of significance.

**Given:** $n = 100$, $p = 0.4800$, $\pi_0 = 0.5000$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi \ge 0.50$ versus $H_1: \pi < 0.50$.
- **Decision rule:** Reject $H_0$ if $z < -1.65$.
- **Test statistic:**
$$z = \frac{p - \pi}{\sqrt{\pi(1 - \pi)/n}} = \frac{0.4800 - 0.5000}{\sqrt{0.5000(0.5000)/100}} = \frac{-0.0200}{0.0500} = -0.40$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.65$).*

**Answer:** $H_0: \pi \ge 0.50$ versus $H_1: \pi < 0.50$; Reject $H_0$ if $z < -1.65$.; $z = -0.40$; Do not reject $H_0$.

✔ *Checker: Exact scipy $z = -0.4000, p = 0.344578$.*

---

## Lind — Chapter 10, Section 10.10: Type II Error

### Exercise 10.27
**Problem:** Refer to Table 10–4 and the example just completed. With $n = 100$, $\sigma = 400$, $\bar{X}_c = 9,922$, and $\mu_1 = 9,880$, verify that the probability of a Type II error is .1469.

**Given:** $n = 100$, $\sigma = 400$, lower critical acceptance boundary $\bar{X}_c = 9,922$, alternative mean $\mu_1 = 9,880$.

Using formula [10–4]:
$$z = \frac{\bar{X}_c - \mu_1}{\sigma / \sqrt{n}} = \frac{9,922 - 9,880}{400 / \sqrt{100}} = \frac{42}{40} = 1.05$$
From Appendix B.1, the area between $0$ and $z = 1.05$ is $.3531$. The probability of failing to reject $H_0$ ($\bar{X} \ge 9,922$) when $\mu_1 = 9,880$ is:
$$\beta = P(z \ge 1.05) = .5000 - .3531 = .1469$$

📘 *Table used: Lind Appendix B.1 ($z = 1.05 \implies .3531$).*

**Answer:** $z = 1.05$; $\beta = .5000 - .3531 = .1469$.

✔ *Checker: Exact `scipy.stats.norm.sf(1.05)` = 0.146859.*

---

### Exercise 10.28
**Problem:** Refer to Table 10–4 and the example just completed. With $n = 100$, $\sigma = 400$, $\bar{X}_c = 9,922$, and $\mu_1 = 9,940$, verify that the probability of a Type II error is .6736.

**Given:** $n = 100$, $\sigma = 400$, lower critical acceptance boundary $\bar{X}_c = 9,922$, alternative mean $\mu_1 = 9,940$.

Using formula [10–4]:
$$z = \frac{\bar{X}_c - \mu_1}{\sigma / \sqrt{n}} = \frac{9,922 - 9,940}{400 / \sqrt{100}} = \frac{-18}{40} = -0.45$$
From Appendix B.1, the area between $0$ and $z = -0.45$ is $.1736$. Because $\bar{X}_c = 9,922$ lies below $\mu_1 = 9,940$, the acceptance region ($\bar{X} \ge 9,922$) covers the area from $-0.45$ to $0$ plus the entire upper half of the curve:
$$\beta = P(z \ge -0.45) = .1736 + .5000 = .6736$$

📘 *Table used: Lind Appendix B.1 ($z = 0.45 \implies .1736$).*

**Answer:** $z = -0.45$; $\beta = .5000 + .1736 = .6736$.

✔ *Checker: Exact `scipy.stats.norm.sf(-0.45)` = 0.673645.*

---

## Lind — Chapter 10: Chapter Exercises

### Exercise 10.29
**Problem:** According to the local union president, the mean gross income of plumbers in the Salt Lake City area follows the normal probability distribution with a mean of $45,000 and a standard deviation of $3,000. A recent investigative reporter for KYAK TV found, for a sample of 120 plumbers, the mean gross income was $45,500. At the .10 significance level, is it reasonable to conclude that the mean income is not equal to $45,000? Determine the p-value.

**Given:** $\mu_0 = 45,000$, $\sigma = 3,000$, $n = 120$, $\bar{X} = 45,500$, $\alpha = .10$.

- **Hypotheses:** $H_0: \mu = 45,000$ versus $H_1: \mu \neq 45,000$.
- **Decision rule ($\alpha = .10$, two-tailed):** Reject $H_0$ if $z < -1.65$ or $z > 1.65$.
- **Test statistic:**
$$z = \frac{45,500 - 45,000}{3,000 / \sqrt{120}} = \frac{500}{273.8613} = 1.83$$
- **Decision:** **Reject $H_0$** because $z = 1.83 > 1.65$. It is reasonable to conclude that the mean gross income is not equal to $45,000.
- **$p$-value:** From Appendix B.1 ($z = 1.83 \implies .4664$), $p\text{-value} = 2(.5000 - .4664) = .0672$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$, $z = 1.83 \implies .4664$).*

**Answer:** Reject $H_0$ ($z = 1.83 > 1.65$); $p\text{-value} = .0672$.

✔ *Checker: Exact scipy $z = 1.8257$, $p = 0.067889$.*

---

### Exercise 10.30
**Problem:** Rutter Nursery Company packages its pine bark mulch in 50-pound bags. From a long history, the production department reports that the distribution of the bag weights follows the normal distribution and the standard deviation of this process is 3 pounds per bag. At the end of each day, Jeff Rutter, the production manager, weighs 10 bags and computes the mean weight of the sample. Below are the weights of 10 bags from today's production: `45.6, 47.7, 47.6, 46.3, 46.2, 47.4, 49.2, 55.8, 47.5, 48.5`.
(a) Can Mr. Rutter conclude that the mean weight of the bags is less than 50 pounds? Use the .01 significance level.
(b) In a brief report, tell why Mr. Rutter can use the z distribution as the test statistic.
(c) Compute the p-value.

**Given:** $\mu_0 = 50$, $\sigma = 3$, $n = 10$, $\bar{X} = \frac{481.8}{10} = 48.18$, $\alpha = .01$.

**(a)**
- **Hypotheses:** $H_0: \mu \ge 50$ versus $H_1: \mu < 50$.
- **Decision rule ($\alpha = .01$, left-tailed):** Reject $H_0$ if $z < -2.33$.
- **Test statistic:**
$$z = \frac{48.18 - 50}{3 / \sqrt{10}} = \frac{-1.82}{0.9487} = -1.92$$
- **Decision:** **Do not reject $H_0$** because $z = -1.92 > -2.33$. Mr. Rutter cannot conclude at the .01 level that the mean bag weight is less than 50 pounds.

**(b)** Mr. Rutter can use the $z$ distribution because the underlying population of bag weights follows the **normal distribution** and the **population standard deviation ($\sigma = 3$ pounds) is known** from long production history.

**(c)** From Appendix B.1, for $z = -1.92$, the area between $0$ and $-1.92$ is $.4726$, so:
$$p\text{-value} = .5000 - .4726 = .0274$$

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -2.33$, $z = -1.92 \implies .4726$).*

**Answer:** (a) $\bar{X} = 48.18$, $z = -1.92 > -2.33$, do not reject $H_0$; (b) population is normal and $\sigma$ is known; (c) $p\text{-value} = .0274$.

✔ *Checker: Exact scipy $z = -1.9184, p = 0.027527$.*

---

### Exercise 10.31
**Problem:** A new weight-watching company, Weight Reducers International, advertises that those who join will lose, on the average, 10 pounds the first two weeks with a standard deviation of 2.8 pounds. A random sample of 50 people who joined the new weight reduction program revealed the mean loss to be 9 pounds. At the .05 level of significance, can we conclude that those joining Weight Reducers on average will lose less than 10 pounds? Determine the p-value.

**Given:** $\mu_0 = 10$, $\sigma = 2.8$, $n = 50$, $\bar{X} = 9$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \ge 10$ versus $H_1: \mu < 10$.
- **Decision rule ($\alpha = .05$, left-tailed):** Reject $H_0$ if $z < -1.65$.
- **Test statistic:**
$$z = \frac{9.0 - 10.0}{2.8 / \sqrt{50}} = \frac{-1.0}{0.39598} = -2.53$$
- **Decision:** **Reject $H_0$** because $z = -2.53 < -1.65$. Conclude that participants lose less than 10 pounds on average.
- **$p$-value:** From Appendix B.1 ($z = -2.53 \implies .4943$), $p\text{-value} = .5000 - .4943 = .0057$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.65$, $z = -2.53 \implies .4943$).*

**Answer:** $z = -2.53 < -1.65$, reject $H_0$; $p\text{-value} = .0057$.

✔ *Checker: Exact scipy $z = -2.5254, p = 0.005778$.*

---

### Exercise 10.32
**Problem:** Dole Pineapple Inc. is concerned that the 16-ounce can of sliced pineapple is being overfilled. Assume the standard deviation of the process is .03 ounces. The quality-control department took a random sample of 50 cans and found that the arithmetic mean weight was 16.05 ounces. At the 5 percent level of significance, can we conclude that the mean weight is greater than 16 ounces? Determine the p-value.

**Given:** $\mu_0 = 16.00$, $\sigma = 0.03$, $n = 50$, $\bar{X} = 16.05$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \le 16.00$ versus $H_1: \mu > 16.00$.
- **Decision rule ($\alpha = .05$, right-tailed):** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{16.05 - 16.00}{0.03 / \sqrt{50}} = \frac{0.05}{0.004243} = 11.79$$
- **Decision:** **Reject $H_0$** because $z = 11.79 > 1.65$. Conclude that the mean weight is greater than 16 ounces.
- **$p$-value:** Since $z = 11.79 > 3.09$, the $p$-value is **virtually $0$** ($.5000 - .5000 = .0000$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $z = 11.79 > 1.65$, reject $H_0$; $p\text{-value} \approx .0000$.

✔ *Checker: Exact scipy $z = 11.7851, p = 2.33 \times 10^{-32}$.*

---

### Exercise 10.33
**Problem:** According to a recent survey, Americans get a mean of 7 hours of sleep per night. A random sample of 50 students at West Virginia University revealed the mean number of hours slept last night was 6 hours and 48 minutes (6.8 hours). The standard deviation of the sample was 0.9 hours. Is it reasonable to conclude that students at West Virginia sleep less than the typical American? Compute the p-value.

**Given:** $\mu_0 = 7.0$, $n = 50$ ($df = 49$), $\bar{X} = 6.8$, $s = 0.9$, $\alpha = .05$ (standard significance level).

- **Hypotheses:** $H_0: \mu \ge 7.0$ versus $H_1: \mu < 7.0$.
- **Decision rule ($df = 49, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.677$.
- **Test statistic:**
$$t = \frac{6.8 - 7.0}{0.9 / \sqrt{50}} = \frac{-0.2}{0.12728} = -1.571$$
- **Decision:** **Do not reject $H_0$** because $t = -1.571 > -1.677$. We cannot conclude that West Virginia University students sleep less than 7 hours on average.
- **$p$-value:** From Appendix B.2 ($df = 49$), $|-1.571|$ lies between $t_{.10} = 1.299$ and $t_{.05} = 1.677$, so the $p$-value is **between .05 and .10** (exact $p = .0613$; or $.0582$ using the normal approximation $z = -1.57$).

📘 *Table used: Lind Appendix B.2 ($df = 49, t_{\text{crit}} = -1.677$).*

**Answer:** $t = -1.571 > -1.677$, do not reject $H_0$; $p$-value is between .05 and .10 (exact $.0613$).

✔ *Checker: Exact scipy $t = -1.5713, p = 0.061273$.*

---

### Exercise 10.34
**Problem:** A statewide real estate sales agency, Farm Associates, specializes in selling farm property in the state of Nebraska. Its records indicate that the mean selling time of farm property is 90 days. Because of recent drought conditions, the agency believes that the mean selling time is now greater than 90 days. A statewide survey of 100 farms sold recently revealed that the mean selling time was 94 days, with a standard deviation of 22 days. At the .10 significance level, has there been an increase in selling time?

**Given:** $\mu_0 = 90$, $n = 100$ ($df = 99$), $\bar{X} = 94$, $s = 22$, $\alpha = .10$.

- **Hypotheses:** $H_0: \mu \le 90$ versus $H_1: \mu > 90$.
- **Decision rule ($df = 99, \alpha = .10$, right-tailed):** Reject $H_0$ if $t > 1.290$ (from Appendix B.2 for $df = 100$).
- **Test statistic:**
$$t = \frac{94 - 90}{22 / \sqrt{100}} = \frac{4}{2.2} = 1.818$$
- **Decision:** **Reject $H_0$** because $t = 1.818 > 1.290$. Conclude that there has been an increase in the mean selling time of farm property.

📘 *Table used: Lind Appendix B.2 ($df = 100, \alpha = .10$ one-tailed $\implies t_{\text{crit}} = 1.290$).*

**Answer:** $t = 1.818 > 1.290$, reject $H_0$; the mean selling time has increased.

✔ *Checker: Exact scipy $t = 1.8182, p = 0.036031$.*

---

### Exercise 10.35
**Problem:** According to the Census Bureau, 3.13 people reside in the typical American household. A sample of 25 households in Arizona retirement communities showed the mean number of residents per household was 2.86 residents. The standard deviation of this sample was 1.20 residents. At the .05 significance level, is it reasonable to conclude the mean number of residents in the retirement community household is less than 3.13 persons?

**Given:** $\mu_0 = 3.13$, $n = 25$ ($df = 24$), $\bar{X} = 2.86$, $s = 1.20$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \ge 3.13$ versus $H_1: \mu < 3.13$.
- **Decision rule ($df = 24, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.711$.
- **Test statistic:**
$$t = \frac{2.86 - 3.13}{1.20 / \sqrt{25}} = \frac{-0.27}{0.24} = -1.125$$
- **Decision:** **Do not reject $H_0$** because $t = -1.125 > -1.711$. We cannot conclude that the mean number of residents in the retirement community household is less than 3.13.

📘 *Table used: Lind Appendix B.2 ($df = 24, t_{\text{crit}} = -1.711$).*

**Answer:** $t = -1.125 > -1.711$, do not reject $H_0$.

✔ *Checker: Exact scipy $t = -1.1250, p = 0.135847$.*

---

### Exercise 10.36
**Problem:** A recent article in Vitality magazine reported that the mean amount of leisure time per week for American men is 40.0 hours. You believe this figure is too large and decide to conduct your own test. In a random sample of 60 men, you find that the mean is 37.8 hours of leisure per week and that the standard deviation of the sample is 12.2 hours. Can you conclude that the information in the article is untrue? Use the .05 significance level. Determine the p-value and explain its meaning.

**Given:** $\mu_0 = 40.0$, $n = 60$ ($df = 59$), $\bar{X} = 37.8$, $s = 12.2$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \ge 40.0$ versus $H_1: \mu < 40.0$ (since you believe 40.0 hours is too large).
- **Decision rule ($df = 59, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.671$ (from Appendix B.2 for $df = 60$).
- **Test statistic:**
$$t = \frac{37.8 - 40.0}{12.2 / \sqrt{60}} = \frac{-2.2}{1.5750} = -1.397$$
- **Decision:** **Do not reject $H_0$** because $t = -1.397 > -1.671$. We cannot conclude that the mean leisure time is less than 40.0 hours.
- **$p$-value:** From Appendix B.2 ($df = 60$), $|-1.397|$ is between $t_{.10} = 1.296$ and $t_{.05} = 1.671$, so the $p$-value is **between .05 and .10** (exact $p = .0838$, or $.0808$ using normal table $z = -1.40$). If the true mean is 40.0 hours, there is about an 8.38% chance of observing a sample mean of 37.8 hours or less by random sampling variation.

📘 *Table used: Lind Appendix B.2 ($df = 60, t_{\text{crit}} = -1.671$).*

**Answer:** $t = -1.397 > -1.671$, do not reject $H_0$; $p$-value is between .05 and .10 (exact $.0838$).

✔ *Checker: Exact scipy $t = -1.3968, p = 0.083847$.*

---

### Exercise 10.37
**Problem:** In recent years, the interest rate on home mortgages has declined to less than 6.0 percent. However, according to a study by the Federal Reserve Board, the rate charged on credit card debt is more than 14 percent. Listed below is the interest rate charged on a sample of 10 credit cards: `14.6, 16.7, 17.4, 17.0, 17.8, 15.4, 13.1, 15.8, 14.3, 14.5`. Is it reasonable to conclude the mean rate charged is greater than 14 percent? Use the .01 significance level.

**Given:** $n = 10$ ($df = 9$), $\mu_0 = 14.0$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 15.6600$, $s = 1.5436$.
- **Hypotheses:** $H_0: \mu \le 14.0$ versus $H_1: \mu > 14.0$.
- **Decision rule:** Reject $H_0$ if $t > 2.821$ ($df = 9, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{15.6600 - 14.0}{1.5436 / \sqrt{10}} = 3.401$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0039$.

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = 2.821$).*

**Answer:** $\bar{X} = 15.6600, s = 1.5436, t = 3.401$; Reject $H_0$; $p\text{-value} = 0.0039$.

✔ *Checker: Exact scipy $t = 3.4008, p = 0.003932$.*

---

### Exercise 10.38
**Problem:** A recent article in The Wall Street Journal reported that the 30-year mortgage rate is now less than 6 percent. A sample of eight small banks in the Midwest revealed the following 30-year rates (in percent): `4.8, 5.3, 6.5, 4.8, 6.1, 5.8, 6.2, 5.6`. At the .01 significance level, can we conclude that the 30-year mortgage rate for small banks is less than 6 percent? Estimate the p-value.

**Given:** $n = 8$ ($df = 7$), $\mu_0 = 6.0$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 5.6375$, $s = 0.6346$.
- **Hypotheses:** $H_0: \mu \ge 6.0$ versus $H_1: \mu < 6.0$.
- **Decision rule:** Reject $H_0$ if $t < -2.998$ ($df = 7, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{5.6375 - 6.0}{0.6346 / \sqrt{8}} = -1.616$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** Exact $p = 0.0751$.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = -2.998$).*

**Answer:** $\bar{X} = 5.6375, s = 0.6346, t = -1.616$; Do not reject $H_0$; $p\text{-value} = 0.0751$.

✔ *Checker: Exact scipy $t = -1.6157, p = 0.075091$.*

---

### Exercise 10.39
**Problem:** According to the Coffee Research Organization (http://www.coffeeresearch.org) the typical American coffee drinker consumes an average of 3.1 cups per day. A sample of 12 senior citizens revealed they consumed the following amounts of coffee, reported in cups, yesterday: `3.1, 3.3, 3.5, 2.6, 2.6, 4.3, 4.4, 3.8, 3.1, 4.1, 3.1, 3.2`. At the .05 significance level, does this sample data suggest there is a difference between the national average and the sample mean from senior citizens?

**Given:** $n = 12$ ($df = 11$), $\mu_0 = 3.1$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 3.4250$, $s = 0.6077$.
- **Hypotheses:** $H_0: \mu = 3.1$ versus $H_1: \mu \neq 3.1$.
- **Decision rule:** Reject $H_0$ if $t < -2.201$ or $t > 2.201$ ($df = 11, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{3.4250 - 3.1}{0.6077 / \sqrt{12}} = 1.853$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** Exact $p = 0.0909$.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 2.201$).*

**Answer:** $\bar{X} = 3.4250, s = 0.6077, t = 1.853$; Do not reject $H_0$; $p\text{-value} = 0.0909$.

✔ *Checker: Exact scipy $t = 1.8526, p = 0.090945$.*

---

### Exercise 10.40
**Problem:** The postanesthesia care area (recovery room) at St. Luke's Hospital in Maumee, Ohio, was recently enlarged. The hope was that with the enlargement the mean number of patients per day would be more than 25. A random sample of 15 days revealed the following numbers of patients: `25, 27, 25, 26, 25, 28, 28, 27, 24, 26, 25, 29, 25, 27, 24`. At the .01 significance level, can we conclude that the mean number of patients per day is more than 25? Estimate the p-value and interpret it.

**Given:** $n = 15$ ($df = 14$), $\mu_0 = 25.0$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 26.0667$, $s = 1.5337$.
- **Hypotheses:** $H_0: \mu \le 25.0$ versus $H_1: \mu > 25.0$.
- **Decision rule:** Reject $H_0$ if $t > 2.624$ ($df = 14, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{26.0667 - 25.0}{1.5337 / \sqrt{15}} = 2.694$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0087$.

📘 *Table used: Lind Appendix B.2 ($df = 14, t_{\text{crit}} = 2.624$).*

**Answer:** $\bar{X} = 26.0667, s = 1.5337, t = 2.694$; Reject $H_0$; $p\text{-value} = 0.0087$.

✔ *Checker: Exact scipy $t = 2.6935, p = 0.008738$.*

---

### Exercise 10.41
**Problem:** www.golfsmith.com receives an average of 6.5 returns per day from online shoppers. For a sample of 12 days, it received the following number of returns: `0, 4, 3, 4, 9, 4, 5, 9, 1, 6, 7, 10`. At the .01 significance level, can we conclude the mean number of returns is less than 6.5?

**Given:** $n = 12$ ($df = 11$), $\mu_0 = 6.5$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 5.1667$, $s = 3.1575$.
- **Hypotheses:** $H_0: \mu \ge 6.5$ versus $H_1: \mu < 6.5$.
- **Decision rule:** Reject $H_0$ if $t < -2.718$ ($df = 11, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{5.1667 - 6.5}{3.1575 / \sqrt{12}} = -1.463$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** Exact $p = 0.0857$.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = -2.718$).*

**Answer:** $\bar{X} = 5.1667, s = 3.1575, t = -1.463$; Do not reject $H_0$; $p\text{-value} = 0.0857$.

✔ *Checker: Exact scipy $t = -1.4628, p = 0.085748$.*

---

### Exercise 10.42
**Problem:** During recent seasons, Major League Baseball has been criticized for the length of the games. A report indicated that the average game lasts 3 hours and 30 minutes. A sample of 17 games revealed the following times to completion: `2.98, 2.40, 2.70, 2.25, 3.23, 3.17, 2.93, 3.18, 2.80, 2.38, 3.75, 3.20, 3.27, 2.52, 2.58, 4.45, 2.45`. Can we conclude that the mean time for a game is less than 3.50 hours? Use the .05 significance level.

**Given:** $n = 17$ ($df = 16$), $\mu_0 = 3.5$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 2.9553$, $s = 0.5596$.
- **Hypotheses:** $H_0: \mu \ge 3.5$ versus $H_1: \mu < 3.5$.
- **Decision rule:** Reject $H_0$ if $t < -1.746$ ($df = 16, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{2.9553 - 3.5}{0.5596 / \sqrt{17}} = -4.014$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0005$.

📘 *Table used: Lind Appendix B.2 ($df = 16, t_{\text{crit}} = -1.746$).*

**Answer:** $\bar{X} = 2.9553, s = 0.5596, t = -4.014$; Reject $H_0$; $p\text{-value} = 0.0005$.

✔ *Checker: Exact scipy $t = -4.0137, p = 0.000501$.*

---

### Exercise 10.43
**Problem:** Watch Corporation of Switzerland claims that its watches on average will neither gain nor lose time during a week. A sample of 18 watches provided the following gains (+) or losses (-) in seconds per week: `-0.38, -0.20, -0.38, -0.32, +0.32, -0.23, +0.30, +0.25, -0.10, -0.37, -0.61, -0.48, -0.47, -0.64, -0.04, -0.20, -0.68, +0.05`. Is it reasonable to conclude that the mean gain or loss in time for the watches is 0? Use the .05 significance level. Estimate the p-value.

**Given:** $n = 18$ ($df = 17$), $\mu_0 = 0.0$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = -0.2322$, $s = 0.3120$.
- **Hypotheses:** $H_0: \mu = 0.0$ versus $H_1: \mu \neq 0.0$.
- **Decision rule:** Reject $H_0$ if $t < -2.110$ or $t > 2.110$ ($df = 17, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{-0.2322 - 0.0}{0.3120 / \sqrt{18}} = -3.158$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0057$.

📘 *Table used: Lind Appendix B.2 ($df = 17, t_{\text{crit}} = 2.110$).*

**Answer:** $\bar{X} = -0.2322, s = 0.3120, t = -3.158$; Reject $H_0$; $p\text{-value} = 0.0057$.

✔ *Checker: Exact scipy $t = -3.1579, p = 0.005744$.*

---

### Exercise 10.44
**Problem:** Listed below is the rate of return for one year (reported in percent) for a sample of 12 mutual funds that are classified as taxable money market funds: `4.63, 4.15, 4.76, 4.70, 4.65, 4.52, 4.70, 5.06, 4.42, 4.51, 4.24, 4.52`. Using the .05 significance level, is it reasonable to conclude that the mean rate of return is more than 4.50 percent?

**Given:** $n = 12$ ($df = 11$), $\mu_0 = 4.5$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 4.5717$, $s = 0.2405$.
- **Hypotheses:** $H_0: \mu \le 4.5$ versus $H_1: \mu > 4.5$.
- **Decision rule:** Reject $H_0$ if $t > 1.796$ ($df = 11, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{4.5717 - 4.5}{0.2405 / \sqrt{12}} = 1.032$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** Exact $p = 0.1621$.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 1.796$).*

**Answer:** $\bar{X} = 4.5717, s = 0.2405, t = 1.032$; Do not reject $H_0$; $p\text{-value} = 0.1621$.

✔ *Checker: Exact scipy $t = 1.0322, p = 0.162077$.*

---

### Exercise 10.45
**Problem:** Many grocery stores and large retailers such as Walmart and Kmart have installed self-checkout systems so shoppers can scan their own items and cash out themselves. How do customers like this service and how often do they use it? Listed below is the number of customers using the service for a sample of 15 days at the Walmart on Highway 544 in Surfside, South Carolina: `120, 108, 120, 114, 118, 91, 118, 92, 104, 104, 112, 97, 118, 108, 117`. Is it reasonable to conclude that the mean number of customers using the self-checkout system is more than 100 per day? Use the .05 significance level.

**Given:** $n = 15$ ($df = 14$), $\mu_0 = 100.0$, $\alpha = 0.05$.

- **Sample statistics:** $\bar{X} = 109.4000$, $s = 9.9628$.
- **Hypotheses:** $H_0: \mu \le 100.0$ versus $H_1: \mu > 100.0$.
- **Decision rule:** Reject $H_0$ if $t > 1.761$ ($df = 14, \alpha = 0.05$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{109.4000 - 100.0}{9.9628 / \sqrt{15}} = 3.654$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0013$.

📘 *Table used: Lind Appendix B.2 ($df = 14, t_{\text{crit}} = 1.761$).*

**Answer:** $\bar{X} = 109.4000, s = 9.9628, t = 3.654$; Reject $H_0$; $p\text{-value} = 0.0013$.

✔ *Checker: Exact scipy $t = 3.6542, p = 0.001302$.*

---

### Exercise 10.46
**Problem:** For a recent year, the mean fare to fly from Charlotte, North Carolina, to Seattle, Washington, on a discount ticket was $267. A random sample of round-trip discount fares on this route last month gives: `$321, $286, $290, $330, $310, $250, $270, $280, $299, $265, $291, $275, $281`. At the .01 significance level, can we conclude that the mean fare has increased? What is the p-value?

**Given:** $n = 13$ ($df = 12$), $\mu_0 = 267.0$, $\alpha = 0.01$.

- **Sample statistics:** $\bar{X} = 288.3077$, $s = 22.4588$.
- **Hypotheses:** $H_0: \mu \le 267.0$ versus $H_1: \mu > 267.0$.
- **Decision rule:** Reject $H_0$ if $t > 2.681$ ($df = 12, \alpha = 0.01$).
- **Test statistic:**
$$t = \frac{\bar{X} - \mu}{s / \sqrt{n}} = \frac{288.3077 - 267.0}{22.4588 / \sqrt{13}} = 3.421$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** Exact $p = 0.0025$.

📘 *Table used: Lind Appendix B.2 ($df = 12, t_{\text{crit}} = 2.681$).*

**Answer:** $\bar{X} = 288.3077, s = 22.4588, t = 3.421$; Reject $H_0$; $p\text{-value} = 0.0025$.

✔ *Checker: Exact scipy $t = 3.4208, p = 0.002536$.*

---

### Exercise 10.47
**Problem:** The publisher of Celebrity Living claims that the mean sales for personality magazines that feature people such as Angelina Jolie or Paris Hilton are 1.5 million copies per week. A sample of 10 comparable titles shows a mean weekly sales last week of 1.3 million copies with a standard deviation of 0.9 million copies. Does this data contradict the publisher's claim? Use the 0.01 significance level.

**Given:** $\mu_0 = 1.5$, $n = 10$ ($df = 9$), $\bar{X} = 1.3$, $s = 0.9$, $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu = 1.5$ versus $H_1: \mu \neq 1.5$.
- **Decision rule ($df = 9, \alpha = .01$, two-tailed):** Reject $H_0$ if $t < -3.250$ or $t > 3.250$.
- **Test statistic:**
$$t = \frac{1.3 - 1.5}{0.9 / \sqrt{10}} = \frac{-0.2}{0.2846} = -0.703$$
- **Decision:** **Do not reject $H_0$** because $-3.250 < -0.703 < 3.250$. The sample data do not contradict the publisher's claim.

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = \pm 3.250$).*

**Answer:** $t = -0.703$; do not reject $H_0$.

✔ *Checker: Exact scipy $t = -0.7027, p = 0.499966$.*

---

### Exercise 10.48
**Problem:** A United Nations report shows the mean family income for Mexican migrants to the United States is $27,000 per year. A FLOC (Farm Labor Organizing Committee) evaluation of 25 Mexican family units reveals a mean to be $30,000 with a sample standard deviation of $10,000. Does this information disagree with the United Nations report? Apply the 0.01 significance level.

**Given:** $\mu_0 = 27,000$, $n = 25$ ($df = 24$), $\bar{X} = 30,000$, $s = 10,000$, $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu = 27,000$ versus $H_1: \mu \neq 27,000$.
- **Decision rule ($df = 24, \alpha = .01$, two-tailed):** Reject $H_0$ if $t < -2.797$ or $t > 2.797$.
- **Test statistic:**
$$t = \frac{30,000 - 27,000}{10,000 / \sqrt{25}} = \frac{3,000}{2,000} = 1.500$$
- **Decision:** **Do not reject $H_0$** because $-2.797 < 1.500 < 2.797$. The sample information does not significantly disagree with the UN report at the .01 level.

📘 *Table used: Lind Appendix B.2 ($df = 24, t_{\text{crit}} = \pm 2.797$).*

**Answer:** $t = 1.500$; do not reject $H_0$.

✔ *Checker: Exact scipy $t = 1.5000, p = 0.146672$.*

---

### Exercise 10.49
**Problem:** A coin toss is used to decide which team gets the ball first in most sports. It involves little effort and is believed to give each side the same chance. In 43 Super Bowl games, the National Football Conference has won the coin-flip 29 times. Meanwhile, the American Football Conference has won only 14 times. Use the five-step hypothesis-testing procedure at the .01 significance level to test whether this data suggests a fair coin flip.
(a) Why can you employ z as the test statistic?
(b) State the null and alternate hypotheses.
(c) Make a diagram of the decision rule.
(d) Evaluate the test statistic and make the decision.
(e) What is the p-value and what does that imply?

**Given:** $n = 43$, $X = 29$ ($p = 29/43 = .6744$), $\pi_0 = .50$, $\alpha = .01$.

**(a)** We can employ $z$ because this is a binomial experiment with $n\pi = 43(.50) = 21.5 \ge 5$ and $n(1-\pi) = 43(.50) = 21.5 \ge 5$.

**(b)** $H_0: \pi = .50$ versus $H_1: \pi \neq .50$.

**(c)** Two-tailed decision rule at $\alpha = .01$ ($\alpha/2 = .005$ in each tail): Reject $H_0$ if $z < -2.58$ (or $-2.576$) or $z > 2.58$ (or $2.576$).

**(d)** Test statistic:
$$z = \frac{(29/43) - .50}{\sqrt{.50(1 - .50)/43}} = \frac{.6744 - .50}{.07625} = 2.29$$
Since $-2.58 < 2.29 < 2.58$, **do not reject $H_0$**. The data do not prove that the Super Bowl coin flip is biased at the .01 significance level.

**(e)** From Appendix B.1 ($z = 2.29 \implies .4890$), $p\text{-value} = 2(.5000 - .4890) = .0220$. A result this extreme occurs about 2.2% of the time (roughly 1 in 45) with a fair coin.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = \pm 2.58, z = 2.29 \implies .4890$).*

**Answer:** (a) Binomial with $n\pi = n(1-\pi) = 21.5 \ge 5$; (b) $H_0: \pi = .50, H_1: \pi \neq .50$; (c) reject $H_0$ if $|z| > 2.58$; (d) $z = 2.29$, do not reject $H_0$; (e) $p\text{-value} = .0220$.

✔ *Checker: Exact scipy $z = 2.2875, p = 0.022167$.*

---

### Exercise 10.50
**Problem:** According to a study by the American Pet Food Dealers Association, 63 percent of U.S. households own pets. A report is being prepared for an editorial in the San Francisco Chronicle. As a part of the editorial, a random sample of 300 households showed 210 own pets. Does this data disagree with the Pet Food Dealers Association data? Use a .05 level of significance.

**Given:** $n = 300$, $X = 210$ ($p = 0.7000$), $\pi_0 = 0.63$, $\alpha = 0.05$.
- **Hypotheses:** $H_0: \pi = 0.63$ versus $H_1: \pi \neq 0.63$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Test statistic:**
$$z = \frac{0.7000 - 0.63}{\sqrt{0.63(0.37)/300}} = \frac{0.0700}{0.0279} = 2.51$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.51 \implies 0.4940$), $p\text{-value} = 0.0120$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96, z = 2.51$).*

**Answer:** $H_0: \pi = 0.63$ versus $H_1: \pi \neq 0.63$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = 2.51$; Reject $H_0$; $p\text{-value} = 0.0120$.

✔ *Checker: Exact scipy $z = 2.5112, p = 0.012031$.*

---

### Exercise 10.51
**Problem:** Tina Dennis is the comptroller for Meek Industries. She believes that the current cash-flow problem at Meek is due to the slow collection of accounts receivable. She believes that more than 60 percent of the accounts are in arrears more than three months. A random sample of 200 accounts showed that 140 were more than three months old. At the .01 significance level, can she conclude that more than 60 percent of the accounts are in arrears for more than three months?

**Given:** $n = 200$, $X = 140$ ($p = 0.7000$), $\pi_0 = 0.60$, $\alpha = 0.01$.
- **Hypotheses:** $H_0: \pi \le 0.60$ versus $H_1: \pi > 0.60$.
- **Decision rule:** Reject $H_0$ if $z > 2.33$.
- **Test statistic:**
$$z = \frac{0.7000 - 0.60}{\sqrt{0.60(0.40)/200}} = \frac{0.1000}{0.0346} = 2.89$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.89 \implies 0.4981$), $p\text{-value} = 0.0019$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33, z = 2.89$).*

**Answer:** $H_0: \pi \le 0.60$ versus $H_1: \pi > 0.60$; Reject $H_0$ if $z > 2.33$.; $z = 2.89$; Reject $H_0$; $p\text{-value} = 0.0019$.

✔ *Checker: Exact scipy $z = 2.8868, p = 0.001946$.*

---

### Exercise 10.52
**Problem:** The policy of the Suburban Transit Authority is to add a bus route if more than 55 percent of the potential commuters indicate they would use the particular route. A sample of 70 commuters revealed that 42 would use a proposed route from Bowman Park to the downtown area. Does the Bowman-to-downtown route meet the STA criterion? Use the .05 significance level.

**Given:** $n = 70$, $X = 42$ ($p = 0.6000$), $\pi_0 = 0.55$, $\alpha = 0.05$.
- **Hypotheses:** $H_0: \pi \le 0.55$ versus $H_1: \pi > 0.55$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{0.6000 - 0.55}{\sqrt{0.55(0.45)/70}} = \frac{0.0500}{0.0595} = 0.84$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 0.84 \implies 0.2995$), $p\text{-value} = 0.2005$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65, z = 0.84$).*

**Answer:** $H_0: \pi \le 0.55$ versus $H_1: \pi > 0.55$; Reject $H_0$ if $z > 1.65$.; $z = 0.84$; Do not reject $H_0$; $p\text{-value} = 0.2005$.

✔ *Checker: Exact scipy $z = 0.8409, p = 0.200209$.*

---

### Exercise 10.53
**Problem:** Past experience at the Crowder Travel Agency indicated that 44 percent of those persons who wanted the agency to plan a vacation for them wanted to go to Europe. During the most recent busy season, a sampling of 1,000 plans was selected at random from the files. It was found that 480 persons wanted to go to Europe on vacation. Has there been a significant shift upward in the percentage of persons who want to go to Europe? Test at the .05 significance level.

**Given:** $n = 1000$, $X = 480$ ($p = 0.4800$), $\pi_0 = 0.44$, $\alpha = 0.05$.
- **Hypotheses:** $H_0: \pi \le 0.44$ versus $H_1: \pi > 0.44$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{0.4800 - 0.44}{\sqrt{0.44(0.56)/1000}} = \frac{0.0400}{0.0157} = 2.55$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.55 \implies 0.4946$), $p\text{-value} = 0.0054$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65, z = 2.55$).*

**Answer:** $H_0: \pi \le 0.44$ versus $H_1: \pi > 0.44$; Reject $H_0$ if $z > 1.65$.; $z = 2.55$; Reject $H_0$; $p\text{-value} = 0.0054$.

✔ *Checker: Exact scipy $z = 2.5482, p = 0.005413$.*

---

### Exercise 10.54
**Problem:** Research in the gaming industry showed that 10 percent of all slot machines in the United States stop working each year. Short's Game Arcade has 60 slot machines and only 3 failed last year. Use the five-step hypothesis-testing procedure at the .05 significance level to test whether this data contradicts the research report.
(a) Why can you employ z as the test statistic?
(b) State the null and alternate hypotheses.
(c) Evaluate the test statistic and make the decision.
(d) What is the p-value and what does that imply?

**Given:** $n = 60$, $X = 3$ ($p = 0.0500$), $\pi_0 = 0.10$, $\alpha = 0.05$.
- **Binomial check:** $n\pi = 6.0 \ge 5$ and $n(1-\pi) = 54.0 \ge 5$, so $z$ is valid.
- **Hypotheses:** $H_0: \pi = 0.10$ versus $H_1: \pi \neq 0.10$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Test statistic:**
$$z = \frac{0.0500 - 0.10}{\sqrt{0.10(0.90)/60}} = \frac{-0.0500}{0.0387} = -1.29$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -1.29 \implies 0.4015$), $p\text{-value} = 0.1970$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96, z = -1.29$).*

**Answer:** $H_0: \pi = 0.10$ versus $H_1: \pi \neq 0.10$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = -1.29$; Do not reject $H_0$; $p\text{-value} = 0.1970$.

✔ *Checker: Exact scipy $z = -1.2910, p = 0.196706$.*

---

### Exercise 10.55
**Problem:** An urban planner claims that, nationally, 20 percent of all families renting condominiums move during a given year. A random sample of 200 families renting condominiums in the Dallas Metroplex revealed that 56 had moved during the past year. At the .01 significance level, does this evidence suggest that a larger proportion of condominium owners moved in the Dallas area? Determine the p-value.

**Given:** $n = 200$, $X = 56$ ($p = 0.2800$), $\pi_0 = 0.20$, $\alpha = 0.01$.
- **Hypotheses:** $H_0: \pi \le 0.20$ versus $H_1: \pi > 0.20$.
- **Decision rule:** Reject $H_0$ if $z > 2.33$.
- **Test statistic:**
$$z = \frac{0.2800 - 0.20}{\sqrt{0.20(0.80)/200}} = \frac{0.0800}{0.0283} = 2.83$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.83 \implies 0.4977$), $p\text{-value} = 0.0023$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33, z = 2.83$).*

**Answer:** $H_0: \pi \le 0.20$ versus $H_1: \pi > 0.20$; Reject $H_0$ if $z > 2.33$.; $z = 2.83$; Reject $H_0$; $p\text{-value} = 0.0023$.

✔ *Checker: Exact scipy $z = 2.8284, p = 0.002339$.*

---

### Exercise 10.56
**Problem:** The cost of weddings in the United States has skyrocketed in recent years. As a result, many couples are opting to have their weddings in the Caribbean. A Caribbean vacation resort recently advertised in Bride Magazine that the cost of a Caribbean wedding was less than $10,000. Listed below is a total cost in $000 for a sample of 8 Caribbean weddings: `9.7, 9.4, 11.7, 9.0, 9.1, 10.5, 9.1, 9.8`. At the .05 significance level is it reasonable to conclude the mean wedding cost is less than $10,000 as advertised?

**Given:** $n = 8$ ($df = 7$), $\mu_0 = 10.0$ ($000), $\alpha = .05$.

- **Sample statistics:** $\bar{X} = \frac{78.3}{8} = 9.7875$, $s = 0.9172$.
- **Hypotheses:** $H_0: \mu \ge 10.0$ versus $H_1: \mu < 10.0$.
- **Decision rule ($df = 7, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.895$.
- **Test statistic:**
$$t = \frac{9.7875 - 10.0}{0.9172 / \sqrt{8}} = \frac{-0.2125}{0.3282} = -0.655$$
- **Decision:** **Do not reject $H_0$** because $t = -0.655 > -1.895$. We cannot conclude that the mean wedding cost is less than $10,000.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = -1.895$).*

**Answer:** $\bar{X} = 9.7875, s = 0.9280, t = -0.655 > -1.895$; do not reject $H_0$.

✔ *Checker: Exact scipy $t = -0.6553, p = 0.266605$.*

---

### Exercise 10.57
**Problem:** According to an ABC News survey, 40 percent of Americans do not eat breakfast. A sample of 30 college students found 16 had skipped breakfast that day. Use the .01 significance level to check whether college students are more likely to skip breakfast.

**Given:** $n = 30$, $X = 16$ ($p = 16/30 = .5333$), $\pi_0 = .40$, $\alpha = .01$.

- **Hypotheses:** $H_0: \pi \le .40$ versus $H_1: \pi > .40$.
- **Decision rule ($\alpha = .01$, right-tailed):** Reject $H_0$ if $z > 2.33$ (or $2.326$).
- **Test statistic:**
$$z = \frac{(16/30) - .40}{\sqrt{.40(.60)/30}} = \frac{.1333}{.08944} = 1.49$$
- **Decision:** **Do not reject $H_0$** because $z = 1.49 < 2.33$. The data do not show that college students are more likely to skip breakfast.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33$).*

**Answer:** $z = 1.49 < 2.33$; do not reject $H_0$.

✔ *Checker: Exact scipy $z = 1.4907, p = 0.068019$.*

---

### Exercise 10.58
**Problem:** After a losing season, there is a great uproar to fire the head football coach. In a random sample of 200 college alumni, 80 favor keeping the coach. Test at the .05 level of significance whether the proportion of alumni who support the coach is less than 50 percent.

**Given:** $n = 200$, $X = 80$ ($p = .40$), $\pi_0 = .50$, $\alpha = .05$.

- **Hypotheses:** $H_0: \pi \ge .50$ versus $H_1: \pi < .50$.
- **Decision rule ($\alpha = .05$, left-tailed):** Reject $H_0$ if $z < -1.65$.
- **Test statistic:**
$$z = \frac{.40 - .50}{\sqrt{.50(.50)/200}} = \frac{-.10}{.03536} = -2.83$$
- **Decision:** **Reject $H_0$** because $z = -2.83 < -1.65$. Conclude that less than 50 percent of the alumni support keeping the coach.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.65$).*

**Answer:** $z = -2.83 < -1.65$; reject $H_0$ (proportion supporting the coach is less than .50).

✔ *Checker: Exact scipy $z = -2.8284, p = 0.002339$.*

---

### Exercise 10.59
**Problem:** During the 1990s, the fatality rate for lung cancer was 80 per 100,000 people. After the turn of the century and the establishment of newer treatments and adjustment in public health advertising, a random sample of 10,000 people exhibits only six deaths due to lung cancer. Test at the .05 significance level whether that data is proof of a reduced fatality rate for lung cancer.

**Given:** $\pi_0 = \frac{80}{100,000} = .0008$, $n = 10,000$, $X = 6$ ($p = .0006$), $\alpha = .05$.

- **Hypotheses:** $H_0: \pi \ge .0008$ versus $H_1: \pi < .0008$.
- **Decision rule ($\alpha = .05$, left-tailed):** Reject $H_0$ if $z < -1.65$ (or $-1.645$).
- **Test statistic:**
$$z = \frac{.0006 - .0008}{\sqrt{.0008(.9992)/10,000}} = \frac{-.0002}{.0002827} = -0.707$$
- **Decision:** **Do not reject $H_0$** because $z = -0.707 > -1.65$. These data do not prove a reduced fatality rate for lung cancer.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.65$).*

**Answer:** $z = -0.707 > -1.65$; do not reject $H_0$.

✔ *Checker: Exact scipy $z = -0.7074, p = 0.239663$.*

---

### Exercise 10.60
**Problem:** The American Water Works Association reports that the per capita water use in a single-family home is 69 gallons per day. Legacy Ranch is a relatively new housing development consisting of 100 homes. The builders installed more efficient water fixtures, such as low-flush toilets, and subsequently conducted a survey of the residences. Thirty-six homes responded, and the sample mean water use per day was 64 gallons with a standard deviation of 8.8 gallons per day. At the .10 level of significance, is that enough evidence to conclude that residents of Legacy Ranch use less water on average?

**Given:** $\mu_0 = 69$, $N = 100$, $n = 36$ ($df = 35$), $\bar{X} = 64$, $s = 8.8$, $\alpha = .10$.

- **Hypotheses:** $H_0: \mu \ge 69$ versus $H_1: \mu < 69$.
- **Decision rule ($df = 35, \alpha = .10$, left-tailed):** Reject $H_0$ if $t < -1.306$.
- **Test statistic (without FPC):**
$$t = \frac{64 - 69}{8.8 / \sqrt{36}} = \frac{-5}{1.4667} = -3.409$$
*(Note: Even if the finite population correction factor $\sqrt{(100-36)/(100-1)} = 0.8040$ is applied since $n/N = .36 > .05$, $t_{\text{FPC}} = \frac{-5}{1.4667(0.8040)} = -4.240$, which is even more extreme.)*
- **Decision:** **Reject $H_0$** because $t = -3.409 < -1.306$. There is sufficient evidence to conclude that residents of Legacy Ranch use less water on average.

📘 *Table used: Lind Appendix B.2 ($df = 35, t_{\text{crit}} = -1.306$).*

**Answer:** $t = -3.409 < -1.306$ (or $t_{\text{FPC}} = -4.240$); reject $H_0$ (Legacy Ranch residents use less water on average).

✔ *Checker: Exact scipy $t = -3.4091, p = 0.000826$.*

---

### Exercise 10.61
**Problem:** A cola-dispensing machine is set to dispense 9.00 ounces of cola per cup, with a standard deviation of 1.00 ounces. The manufacturer of the machine would like to set the control limit in such a way that, for samples of 36, 5 percent of the sample means will be greater than the upper control limit, and 5 percent of the sample means will be less than the lower control limit.
(a) At what value should the control limit be set?
(b) What is the probability that if the population mean shifts to 8.9, this change will not be detected?
(c) What is the probability that if the population mean shifts to 9.3, this change will not be detected?

**Given:** $\mu_0 = 9.00$, $\sigma = 1.00$, $n = 36$, upper and lower tail probabilities $= .05$ each ($z = \pm 1.65$).

**(a)** Control limits:
$$\bar{X}_c = \mu_0 \pm z \frac{\sigma}{\sqrt{n}} = 9.00 \pm 1.65 \left(\frac{1.00}{\sqrt{36}}\right) = 9.00 \pm 0.275 \implies \mathbf{8.725\text{ and }9.275}$$

**(b)** If $\mu_1 = 8.9$, the change is not detected when $8.725 \le \bar{X} \le 9.275$. Using Lind Appendix C's single-boundary calculation at the closer limit $\bar{X}_c = 8.725$:
$$z = \frac{8.725 - 8.900}{1.00 / \sqrt{36}} = \frac{-0.175}{0.1667} = -1.05 \implies P(z > -1.05) = .5000 + .3531 = .8531$$
*(Note: Subtracting the tiny upper-tail area above $9.275$, where $z = (9.275-8.9)/(1/6) = 2.25 \implies .5000 - .4878 = .0122$, gives $.8531 - .0122 = .8409$.)*

**(c)** If $\mu_1 = 9.3$, at the upper control limit $\bar{X}_c = 9.275$:
$$z = \frac{9.275 - 9.300}{1.00 / \sqrt{36}} = \frac{-0.025}{0.1667} = -0.15 \implies P(z < -0.15) = .5000 - .0596 = .4404$$

📘 *Table used: Lind Appendix B.1 ($z = 1.65, z = -1.05 \implies .3531, z = -0.15 \implies .0596$).*

**Answer:** (a) $8.725$ and $9.275$; (b) $.8531$ (or $.8409$ between both limits); (c) $.4404$.

✔ *Checker: Matches Lind Appendix C verbatim (8.725 and 9.275; 0.8531; 0.4404).*

---

### Exercise 10.62
**Problem:** The owners of the Westfield Mall wished to study customer shopping habits. From earlier studies, the owners were under the impression that a typical shopper spends 0.75 hours at the mall, with a standard deviation of 0.10 hours. Recently the mall owners added some specialty restaurants designed to keep shoppers in the mall longer. The consulting firm, Brunner and Swanson Marketing Enterprises, was hired to evaluate the effects of the restaurants. A sample of 45 shoppers by Brunner and Swanson revealed that the mean time spent in the mall had increased to 0.80 hours.
(a) Develop a test of hypothesis to determine if the mean time spent in the mall is more than 0.75 hours. Use the .05 significance level.
(b) Suppose the mean shopping time actually increased from 0.75 hours to 0.77 hours. What is the probability this increase would not be detected?
(c) When Brunner and Swanson reported the information in part (b) to the mall owners, the owners were upset with the statement that a survey could not detect a change from 0.75 to 0.77 hours of shopping time. How could this probability be reduced?

**Given:** $\mu_0 = 0.75$, $\sigma = 0.10$, $n = 45$, $\bar{X} = 0.80$, $\alpha = .05$.

**(a)**
- **Hypotheses:** $H_0: \mu \le 0.75$ versus $H_1: \mu > 0.75$.
- **Decision rule ($\alpha = .05$, right-tailed):** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{0.80 - 0.75}{0.10 / \sqrt{45}} = \frac{0.05}{0.014907} = 3.35$$
- **Decision:** **Reject $H_0$** ($z = 3.35 > 1.65$). Conclude that the mean shopping time is more than 0.75 hours.

**(b)** First find the critical sample mean $\bar{X}_c$ for rejecting $H_0$:
$$\bar{X}_c = 0.75 + 1.65\left(\frac{0.10}{\sqrt{45}}\right) = 0.75 + 0.0246 = 0.7746\text{ hours}$$
If $\mu_1 = 0.77$, the increase is not detected when $\bar{X} \le 0.7746$:
$$z = \frac{0.7746 - 0.77}{0.10 / \sqrt{45}} = \frac{0.0046}{0.014907} = 0.31$$
From Appendix B.1 ($z = 0.31 \implies .1217$), the Type II error probability is:
$$\beta = P(z \le 0.31) = .5000 + .1217 = .6217$$

**(c)** To reduce the probability of a Type II error ($\beta$), the mall owners can **increase the sample size $n$** (or increase the significance level $\alpha$, e.g., from $.05$ to $.10$).

📘 *Table used: Lind Appendix B.1 ($z = 1.65, z = 0.31 \implies .1217$).*

**Answer:** (a) $z = 3.35 > 1.65$, reject $H_0$; (b) $\bar{X}_c = 0.7746, z = 0.31 \implies \beta = .6217$; (c) increase the sample size $n$ (or increase $\alpha$).

✔ *Checker: Exact scipy $\bar{X}_c = 0.7745, \beta = 0.6203$.*

---

### Exercise 10.63
**Problem:** The following null and alternate hypotheses are given: $H_0: \mu \le 50$ and $H_1: \mu > 50$. Suppose the population standard deviation is 10. The probability of a Type I error is set at .01 and the probability of a Type II error at .30. Assume that the population mean shifts from 50 to 55. How large a sample is necessary to meet these requirements?

**Given:** $\mu_0 = 50$, $\mu_1 = 55$, $\sigma = 10$, $\alpha = .01$ ($z_{.01} = 2.33$), $\beta = .30$ ($z_{.30} = 0.525$, since area $.5000 - .3000 = .2000$ lies between $z = 0.52$ and $z = 0.53$).

Equating the critical value $\bar{X}_c$ from both distributions:
$$50 + 2.33\left(\frac{10}{\sqrt{n}}\right) = 55 - 0.525\left(\frac{10}{\sqrt{n}}\right)$$
$$\frac{28.55}{\sqrt{n}} = 5 \implies \sqrt{n} = \frac{28.55}{5} = 5.71 \implies n = (5.71)^2 = 32.60 \implies \mathbf{33}$$

📘 *Table used: Lind Appendix B.1 ($z_{.01} = 2.33$, $z_{.30} = 0.525$).*

**Answer:** $n = 32.6 \implies 33$.

✔ *Checker: Matches Lind Appendix C verbatim ($n = (5.71)^2 = 32.6 \implies 33$).*

---

### Exercise 10.64
**Problem:** An insurance company, based on past experience, estimates the mean damage for a natural disaster in its area is $5,000. After introducing several plans to prevent loss, it randomly samples 200 policyholders and finds the mean amount per claim was $4,800 with a standard deviation of $1,300. Does it appear the prevention plans were effective in reducing the mean amount of a claim? Use the .05 significance level.

**Given:** $\mu_0 = 5,000$, $n = 200$ ($df = 199$), $\bar{X} = 4,800$, $s = 1,300$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \ge 5,000$ versus $H_1: \mu < 5,000$.
- **Decision rule ($df = 199, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.653$ (from Appendix B.2 for $df = 200$, or $z < -1.65$).
- **Test statistic:**
$$t = \frac{4,800 - 5,000}{1,300 / \sqrt{200}} = \frac{-200}{91.9239} = -2.176$$
- **Decision:** **Reject $H_0$** because $t = -2.176 < -1.653$. The prevention plans appear effective in reducing the mean claim amount.

📘 *Table used: Lind Appendix B.2 ($df = 200, t_{\text{crit}} = -1.653$).*

**Answer:** $t = -2.176 < -1.653$; reject $H_0$ (prevention plans reduced the mean claim amount).

✔ *Checker: Exact scipy $t = -2.1757, p = 0.015368$.*

---

### Exercise 10.65
**Problem:** A national grocer's magazine reports the typical shopper spends eight minutes in line waiting to check out. A sample of 24 shoppers at the local Farmer Jack's showed a mean of 7.5 minutes with a standard deviation of 3.2 minutes. Is the waiting time at the local Farmer Jack's less than that reported in the national magazine? Use the .05 significance level.

**Given:** $\mu_0 = 8.0$, $n = 24$ ($df = 23$), $\bar{X} = 7.5$, $s = 3.2$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \ge 8.0$ versus $H_1: \mu < 8.0$.
- **Decision rule ($df = 23, \alpha = .05$, left-tailed):** Reject $H_0$ if $t < -1.714$.
- **Test statistic:**
$$t = \frac{7.5 - 8.0}{3.2 / \sqrt{24}} = \frac{-0.5}{0.6532} = -0.765$$
- **Decision:** **Do not reject $H_0$** because $t = -0.765 > -1.714$. We cannot conclude that the waiting time at the local Farmer Jack's is less than 8 minutes.

📘 *Table used: Lind Appendix B.2 ($df = 23, t_{\text{crit}} = -1.714$).*

**Answer:** $t = -0.765 > -1.714$; do not reject $H_0$.

✔ *Checker: Exact scipy $t = -0.7655, p = 0.225921$.*

---

## Lind — Chapter 10: Data Set Exercises

### Exercise 10.66
**Problem:** Refer to the Real Estate data, which report information on the homes sold in Goodyear, Arizona, last year.
(a) A recent article in the Arizona Republic indicated that the mean selling price of the homes in the area is more than $220,000. Can we conclude that the mean selling price in the Goodyear, AZ, area is more than $220,000? Use the .01 significance level. What is the p-value?
(b) The same article reported the mean size was more than 2,100 square feet. Can we conclude that the mean size of homes sold in the Goodyear, AZ, area is more than 2,100 square feet? Use the .01 significance level. What is the p-value?
(c) Determine the proportion of homes that have an attached garage. At the .05 significance level, can we conclude that more than 60 percent of the homes sold in the Goodyear, AZ, area had an attached garage? What is the p-value?
(d) Determine the proportion of homes that have a pool. At the .05 significance level, can we conclude that more than 60 percent of the homes sold in the Goodyear, AZ, area had a pool? What is the p-value?

**Given:** Appendix A.1 Real Estate dataset ($n = 105$ homes, $df = 104$).

**(a) Mean selling price ($\mu_0 = 220$ thousand, $\alpha = .01$):**
- $H_0: \mu \le 220$ versus $H_1: \mu > 220$; reject $H_0$ if $t > 2.363$ ($df = 104$).
- Sample statistics: $\bar{X} = 221.1029$, $s = 47.1054$.
$$t = \frac{221.1029 - 220}{47.1054 / \sqrt{105}} = 0.240, \qquad p\text{-value} = 0.4054$$
- **Do not reject $H_0$** ($t = 0.240 < 2.363$). We cannot conclude the mean selling price is more than $220,000.

**(b) Mean home size ($\mu_0 = 2,100$ sq. ft., $\alpha = .01$):**
- $H_0: \mu \le 2,100$ versus $H_1: \mu > 2,100$; reject $H_0$ if $t > 2.363$.
- Sample statistics: $\bar{X} = 2223.8095$, $s = 248.6594$.
$$t = \frac{2223.8095 - 2,100}{248.6594 / \sqrt{105}} = 5.102, \qquad p\text{-value} = 0.000001 \approx .0000$$
- **Reject $H_0$** ($t = 5.102 > 2.363$). Conclude that the mean home size is more than 2,100 square feet.

**(c) Proportion with attached garage ($\pi_0 = .60, \alpha = .05$):**
- $H_0: \pi \le .60$ versus $H_1: \pi > .60$; reject $H_0$ if $z > 1.65$.
- Sample proportion: $p = \frac{71}{105} = 0.6762$.
$$z = \frac{0.6762 - .60}{\sqrt{.60(.40)/105}} = \frac{.0762}{.04781} = 1.59, \qquad p\text{-value} = 0.0555$$
- **Do not reject $H_0$** ($z = 1.59 < 1.65$). We cannot conclude that more than 60% have an attached garage.

**(d) Proportion with a pool ($\pi_0 = .60, \alpha = .05$):**
- $H_0: \pi \le .60$ versus $H_1: \pi > .60$; reject $H_0$ if $z > 1.65$.
- Sample proportion: $p = \frac{67}{105} = 0.6381$.
$$z = \frac{0.6381 - .60}{\sqrt{.60(.40)/105}} = \frac{.0381}{.04781} = 0.80, \qquad p\text{-value} = 0.2128$$
- **Do not reject $H_0$** ($z = 0.80 < 1.65$). We cannot conclude that more than 60% have a pool.

📘 *Table used: Lind Appendix B.1 and B.2.*

**Answer:** (a) $t = 0.240, p = 0.4054$, do not reject $H_0$; (b) $t = 5.102, p \approx .0000$, reject $H_0$; (c) $p = .6762, z = 1.59, p\text{-value} = 0.0555$, do not reject $H_0$; (d) $p = .6381, z = 0.80, p\text{-value} = 0.2128$, do not reject $H_0$.

✔ *Checker: Verified directly from Appendix A.1 dataset ($N = 105$).*

---

### Exercise 10.67
**Problem:** Refer to the Baseball 2009 data, which report information on the 30 Major League Baseball teams for the 2009 season.
(a) Conduct a test of hypothesis to determine whether the mean salary of the teams was different from $80.0 million. Use the .05 significance level.
(b) Conduct a test of hypothesis to determine whether the mean attendance was more than 2,000,000 per team.

**Given:** Appendix A.2 Baseball 2009 dataset ($n = 30$ teams, $df = 29$).

**(a) Team salary ($\mu_0 = 80.0$ million, $\alpha = .05$):**
- $H_0: \mu = 80.0$ versus $H_1: \mu \neq 80.0$; reject $H_0$ if $t < -2.045$ or $t > 2.045$.
- Sample statistics: $\bar{X} = 88.51$, $s = 33.90$.
$$t = \frac{88.51 - 80.0}{33.90 / \sqrt{30}} = \frac{8.5133}{6.1895} = 1.38, \qquad p\text{-value} = 0.1795$$
- **Do not reject $H_0$** ($-2.045 < 1.38 < 2.045$). The mean team salary is not significantly different from $80.0 million.

**(b) Team attendance ($\mu_0 = 2.0$ million, $\alpha = .05$):**
- $H_0: \mu \le 2.0$ versus $H_1: \mu > 2.0$; reject $H_0$ if $t > 1.699$.
- Sample statistics: $\bar{X} = 2.4477$ million ($2,447,667$), $s = 0.6983$ million ($698,348$).
$$t = \frac{2.4477 - 2.0}{0.6983 / \sqrt{30}} = 3.51, \qquad p\text{-value} = 0.0007$$
- **Reject $H_0$** ($t = 3.51 > 1.699$). Conclude that the mean attendance was more than 2,000,000 per team.

📘 *Table used: Lind Appendix B.2 ($df = 29, t_{.05,\text{two-tailed}} = 2.045, t_{.05,\text{one-tailed}} = 1.699$).*

**Answer:** (a) $\bar{X} = 88.51, s = 33.90, t = 1.38$, do not reject $H_0$; (b) $\bar{X} = 2.448\text{M}, s = 0.698\text{M}, t = 3.51 > 1.699$, reject $H_0$ (mean attendance is over 2,000,000).

✔ *Checker: Matches Lind Appendix C verbatim ($t = 1.38$, do not reject; $t = 3.51$, reject).*

---

### Exercise 10.68
**Problem:** Refer to the Buena School District bus data.
(a) Select the variable for the number of miles traveled last month. Conduct a test of hypothesis to determine whether the mean number of miles traveled is equal to 840. Use the .01 significance level. Find the p-value and explain what it means.
(b) Using the maintenance cost variable, conduct a test of hypothesis to determine whether the mean maintenance cost is less than $500 at the .05 significance level. Determine the p-value and interpret the result.
(c) Suppose we consider a bus "old" if it is more than eight years old. At the .01 significance level, can we conclude that less than 40 percent of the buses are old? Report the p-value.

**Given:** Appendix A.3 Buena School District Bus dataset ($n = 80$ buses, $df = 79$).

**(a) Mean miles traveled ($\mu_0 = 840, \alpha = .01$):**
- $H_0: \mu = 840$ versus $H_1: \mu \neq 840$; reject $H_0$ if $t < -2.639$ or $t > 2.639$ ($df = 79$).
- Sample statistics: $\bar{X} = 830.1125$, $s = 42.1882$.
$$t = \frac{830.1125 - 840}{42.1882 / \sqrt{80}} = \frac{-9.8875}{4.7168} = -2.096, \qquad p\text{-value} = 0.0393$$
- **Do not reject $H_0$** at the .01 level ($-2.639 < -2.096 < 2.639$). If $\mu = 840$, there is a 3.93% chance of observing a sample mean this far from 840.

**(b) Mean maintenance cost ($\mu_0 = 500, \alpha = .05$):**
- $H_0: \mu \ge 500$ versus $H_1: \mu < 500$; reject $H_0$ if $t < -1.664$.
- Sample statistics: $\bar{X} = 450.2875$, $s = 53.6860$.
$$t = \frac{450.2875 - 500}{53.6860 / \sqrt{80}} = \frac{-49.7125}{6.0023} = -8.282, \qquad p\text{-value} = 1.2273e-12 \approx .0000$$
- **Reject $H_0$** ($t = -8.282 < -1.664$). Conclude that the mean maintenance cost is significantly less than $500.

**(c) Proportion of old buses ($\text{Age} > 8$, $\pi_0 = .40, \alpha = .01$):**
- $H_0: \pi \ge .40$ versus $H_1: \pi < .40$; reject $H_0$ if $z < -2.33$.
- Sample proportion: $28$ of $80$ buses have $\text{Age} > 8$, so $p = \frac{28}{80} = 0.3500$.
$$z = \frac{0.3500 - .40}{\sqrt{.40(.60)/80}} = \frac{-.0500}{.05477} = -0.91, \qquad p\text{-value} = 0.1807$$
- **Do not reject $H_0$** ($z = -0.91 > -2.33$). We cannot conclude that less than 40% of the buses are old.

📘 *Table used: Lind Appendix B.1 and B.2 ($df = 79$).*

**Answer:** (a) $\bar{X} = 830.11, s = 42.19, t = -2.096, p = 0.0393$, do not reject $H_0$ at $\alpha = .01$; (b) $\bar{X} = 450.29, s = 53.69, t = -8.282, p \approx .0000$, reject $H_0$; (c) $p = .3500, z = -0.91, p = 0.1807$, do not reject $H_0$.

✔ *Checker: Verified directly from Appendix A.3 dataset ($N = 80$).*

---

# Lind — Chapter 11: Two-Sample Tests of Hypothesis

**Scope:** Every exercise in Chapter 11 of Douglas A. Lind, William G. Marchal, and Samuel A. Wathen, *Statistical Techniques in Business & Economics* (15th ed.): Section Exercises 11.1–11.6 (§11.2, pp. 377–378), 11.7–11.12 (§11.3, pp. 381–382), 11.13–11.18 (§11.4, pp. 386–388), 11.19–11.22 (§11.4, pp. 391–392), 11.23–11.26 (§11.6, pp. 398–399), Chapter Exercises 11.27–11.60 (pp. 400–406), and Data Set Exercises 11.61–11.63 (p. 407). Both odd-numbered and unsolved even-numbered exercises are completely worked out.

**How tables were used:** Standard normal areas and critical values follow Lind Appendix B.1, and Student's $t$ critical values follow Lind Appendix B.2 (with Welch degrees of freedom rounded down to an integer per formula [11–8]), alongside exact `scipy.stats` $p$-values in the checker notes.

**Conventions (Lind §§11.1–11.6):**
- Two-sample $z$-test for independent means ($\sigma_1, \sigma_2$ known) [11–2]: $z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}}$.
- Two-sample $z$-test for proportions [11–3, 11–4]: $p_c = \frac{X_1 + X_2}{n_1 + n_2}$ and $z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}}$.
- Pooled two-sample $t$-test ($\sigma_1 = \sigma_2$ unknown) [11–5, 11–6]: $s_p^2 = \frac{(n_1-1)s_1^2 + (n_2-1)s_2^2}{n_1+n_2-2}$ and $t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{s_p^2(1/n_1 + 1/n_2)}}$ with $df = n_1 + n_2 - 2$.
- Unequal-variance two-sample $t$-test ($\sigma_1 \neq \sigma_2$ unknown) [11–7, 11–8]: $t = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{s_1^2/n_1 + s_2^2/n_2}}$ with $df = \left\lfloor \frac{(s_1^2/n_1 + s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}} \right\rfloor$.
- Paired $t$-test for dependent samples [11–9]: $t = \frac{\bar{d}}{s_d / \sqrt{n}}$ with $df = n - 1$.

---

## Lind — Chapter 11, Section 11.2: Independent Samples ($\sigma_1$ and $\sigma_2$ Known)

### Exercise 11.1
**Problem:** A sample of 40 observations is selected from one population with a population standard deviation of 5. The sample mean is 102. A sample of 50 observations is selected from a second population with a population standard deviation of 6. The sample mean is 99. Conduct the following test of hypothesis using the .04 significance level: $H_0: \mu_1 = \mu_2$ and $H_1: \mu_1 \neq \mu_2$.
(a) Is this a one-tailed or a two-tailed test?
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value?

**Given:** $n_1 = 40, \bar{X}_1 = 102, \sigma_1 = 5$; $n_2 = 50, \bar{X}_2 = 99, \sigma_2 = 6$; $\alpha = 0.04$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$ (two-tailed).
- **Decision rule:** Reject $H_0$ if $z < -2.05$ or $z > 2.05$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{102 - 99}{\sqrt{5^2/40 + 6^2/50}} = \frac{3.00}{1.1597} = 2.59$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.59$), $p\text{-value} = 0.0096$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.05, z = 2.59$).*

**Answer:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; Reject $H_0$ if $z < -2.05$ or $z > 2.05$.; $z = 2.59$; Reject $H_0$; $p\text{-value} = 0.0096$.

✔ *Checker: Exact scipy $z = 2.5868, p = 0.009688$.*

---

### Exercise 11.2
**Problem:** A sample of 65 observations is selected from one population with a population standard deviation of 0.75. The sample mean is 2.67. A sample of 50 observations is selected from a second population with a population standard deviation of 0.66. The sample mean is 2.59. Conduct the following test of hypothesis using the .08 significance level: $H_0: \mu_1 \le \mu_2$ and $H_1: \mu_1 > \mu_2$.
(a) Is this a one-tailed or a two-tailed test?
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) What is your decision regarding $H_0$?
(e) What is the p-value?

**Given:** $n_1 = 65, \bar{X}_1 = 2.67, \sigma_1 = 0.75$; $n_2 = 50, \bar{X}_2 = 2.59, \sigma_2 = 0.66$; $\alpha = 0.08$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$ (one-tailed).
- **Decision rule:** Reject $H_0$ if $z > 1.41$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{2.67 - 2.59}{\sqrt{0.75^2/65 + 0.66^2/50}} = \frac{0.08}{0.1318} = 0.61$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 0.61$), $p\text{-value} = 0.2709$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.41, z = 0.61$).*

**Answer:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$; Reject $H_0$ if $z > 1.41$.; $z = 0.61$; Do not reject $H_0$; $p\text{-value} = 0.2709$.

✔ *Checker: Exact scipy $z = 0.6071, p = 0.271901$.*

---

### Exercise 11.3
**Problem:** Gibbs Baby Food Company wishes to compare the weight gain of infants using its brand versus its competitor's. A sample of 40 babies using the Gibbs products revealed a mean weight gain of 7.6 pounds in the first three months after birth. For the Gibbs brand, the population standard deviation of the sample is 2.3 pounds. A sample of 55 babies using the competitor's brand revealed a mean increase in weight of 8.1 pounds. The population standard deviation is 2.9 pounds. At the .05 significance level, can we conclude that babies using the Gibbs brand gained less weight? Compute the p-value and interpret it.

**Given:** $n_1 = 40, \bar{X}_1 = 7.6, \sigma_1 = 2.3$; $n_2 = 55, \bar{X}_2 = 8.1, \sigma_2 = 2.9$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 \ge \mu_2$ versus $H_1: \mu_1 < \mu_2$ (one-tailed).
- **Decision rule:** Reject $H_0$ if $z < -1.65$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{7.6 - 8.1}{\sqrt{2.3^2/40 + 2.9^2/55}} = \frac{-0.50}{0.5340} = -0.94$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -0.94$), $p\text{-value} = 0.1736$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = -1.65, z = -0.94$).*

**Answer:** $H_0: \mu_1 \ge \mu_2$ versus $H_1: \mu_1 < \mu_2$; Reject $H_0$ if $z < -1.65$.; $z = -0.94$; Do not reject $H_0$; $p\text{-value} = 0.1736$.

✔ *Checker: Exact scipy $z = -0.9363, p = 0.174553$.*

---

### Exercise 11.4
**Problem:** As part of a study of corporate employees, the director of human resources for PNC Inc. wants to compare the distance traveled to work by employees at its office in downtown Cincinnati with the distance for those in downtown Pittsburgh. A sample of 35 Cincinnati employees showed they travel a mean of 370 miles per month. A sample of 40 Pittsburgh employees showed they travel a mean of 380 miles per month. The population standard deviation for the Cincinnati and Pittsburgh employees are 30 and 26 miles, respectively. At the .05 significance level, is there a difference in the mean number of miles traveled per month between Cincinnati and Pittsburgh employees?

**Given:** $n_1 = 35, \bar{X}_1 = 370, \sigma_1 = 30$; $n_2 = 40, \bar{X}_2 = 380, \sigma_2 = 26$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$ (two-tailed).
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{370 - 380}{\sqrt{30^2/35 + 26^2/40}} = \frac{-10.00}{6.5280} = -1.53$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -1.53$), $p\text{-value} = 0.1260$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96, z = -1.53$).*

**Answer:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = -1.53$; Do not reject $H_0$; $p\text{-value} = 0.1260$.

✔ *Checker: Exact scipy $z = -1.5319, p = 0.125554$.*

---

### Exercise 11.5
**Problem:** Women's height is a suspected factor for difficult deliveries, that is, shorter women are more likely to have Caesarean sections. A medical researcher found in a sample of 45 women who had a normal delivery that their mean height was 61.4 inches. A second sample of 39 women who had a Caesarean section had a mean height of 60.6 inches. Assume that the population of heights of normal deliveries has a population standard deviation of 1.2 inches. Also assume that the heights of the population of women who had Caesarean section births has a standard deviation of 1.1 inches. Are those who had a Caesarean section shorter? Use the .05 significance level. Find the p-value and explain what it means.

**Given:** $n_1 = 45, \bar{X}_1 = 61.4, \sigma_1 = 1.2$; $n_2 = 39, \bar{X}_2 = 60.6, \sigma_2 = 1.1$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$ (one-tailed).
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{61.4 - 60.6}{\sqrt{1.2^2/45 + 1.1^2/39}} = \frac{0.80}{0.2510} = 3.19$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 3.19$), $p\text{-value} = 0.0007$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65, z = 3.19$).*

**Answer:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$; Reject $H_0$ if $z > 1.65$.; $z = 3.19$; Reject $H_0$; $p\text{-value} = 0.0007$.

✔ *Checker: Exact scipy $z = 3.1866, p = 0.000720$.*

---

### Exercise 11.6
**Problem:** Mary Jo Fitzpatrick is the vice president for Nursing Services at St. Luke's Memorial Hospital. Recently she noticed in the job postings for nurses that those that are unionized seem to offer higher wages. She decided to investigate and gathered the following information: Union ($n_1=40, \bar{X}_1=\$20.75, \sigma_1=\$2.25$) and Nonunion ($n_2=45, \bar{X}_2=\$19.80, \sigma_2=\$1.90$). Would it be reasonable for her to conclude that union nurses earn more? Use the .02 significance level. What is the p-value?

**Given:** $n_1 = 40, \bar{X}_1 = 20.75, \sigma_1 = 2.25$; $n_2 = 45, \bar{X}_2 = 19.8, \sigma_2 = 1.9$; $\alpha = 0.02$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$ (one-tailed).
- **Decision rule:** Reject $H_0$ if $z > 2.05$.
- **Test statistic:**
$$z = \frac{\bar{X}_1 - \bar{X}_2}{\sqrt{\sigma_1^2/n_1 + \sigma_2^2/n_2}} = \frac{20.75 - 19.8}{\sqrt{2.25^2/40 + 1.9^2/45}} = \frac{0.95}{0.4547} = 2.09$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.09$), $p\text{-value} = 0.0183$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.05, z = 2.09$).*

**Answer:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$; Reject $H_0$ if $z > 2.05$.; $z = 2.09$; Reject $H_0$; $p\text{-value} = 0.0183$.

✔ *Checker: Exact scipy $z = 2.0891, p = 0.018348$.*

---

## Lind — Chapter 11, Section 11.3: Two-Sample Tests about Proportions

### Exercise 11.7
**Problem:** The null and alternate hypotheses are: $H_0: \pi_1 \le \pi_2$ and $H_1: \pi_1 > \pi_2$. A sample of 100 observations from the first population indicated that $X_1$ is 70. A sample of 150 observations from the second population revealed $X_2$ to be 90. Use the .05 significance level to test the hypothesis.
(a) State the decision rule.
(b) Compute the pooled proportion.
(c) Compute the value of the test statistic.
(d) What is your decision regarding the null hypothesis?

**Given:** $n_1 = 100, X_1 = 70$ ($p_1 = 0.7000$); $n_2 = 150, X_2 = 90$ ($p_2 = 0.6000$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{70 + 90}{100 + 150} = \frac{160}{250} = 0.6400$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.7000 - 0.6000}{0.0620} = 1.61$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.61$), $p\text{-value} = 0.0537$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.6400$; Reject $H_0$ if $z > 1.65$.; $z = 1.61$; Do not reject $H_0$; $p\text{-value} = 0.0537$.

✔ *Checker: Exact scipy $z = 1.6137, p = 0.053292$.*

---

### Exercise 11.8
**Problem:** The null and alternate hypotheses are: $H_0: \pi_1 = \pi_2$ and $H_1: \pi_1 \neq \pi_2$. A sample of 200 observations from the first population indicated that $X_1$ is 170. A sample of 150 observations from the second population revealed $X_2$ to be 110. Use the .05 significance level to test the hypothesis.
(a) State the decision rule.
(b) Compute the pooled proportion.
(c) Compute the value of the test statistic.
(d) What is your decision regarding the null hypothesis?

**Given:** $n_1 = 200, X_1 = 170$ ($p_1 = 0.8500$); $n_2 = 150, X_2 = 110$ ($p_2 = 0.7333$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{170 + 110}{200 + 150} = \frac{280}{350} = 0.8000$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.8500 - 0.7333}{0.0432} = 2.70$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.70$), $p\text{-value} = 0.0070$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $p_c = 0.8000$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = 2.70$; Reject $H_0$; $p\text{-value} = 0.0070$.

✔ *Checker: Exact scipy $z = 2.7003, p = 0.006928$.*

---

### Exercise 11.9
**Problem:** The Damon family owns a large grape vineyard in western New York along Lake Erie. The grapevines must be sprayed at the beginning of the growing season to protect against various insects and diseases. Two new insecticides have just been marketed: Pernod 5 and Action. When the grapes ripened, 400 of the vines treated with Pernod 5 were checked for infestation ($X_1 = 24$). Likewise, a sample of 400 vines sprayed with Action were checked ($X_2 = 40$). At the .05 significance level, can we conclude that there is a difference in the proportion of vines infested using Pernod 5 as opposed to Action?

**Given:** $n_1 = 400, X_1 = 24$ ($p_1 = 0.0600$); $n_2 = 400, X_2 = 40$ ($p_2 = 0.1000$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{24 + 40}{400 + 400} = \frac{64}{800} = 0.0800$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.0600 - 0.1000}{0.0192} = -2.09$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -2.09$), $p\text{-value} = 0.0366$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $p_c = 0.0800$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = -2.09$; Reject $H_0$; $p\text{-value} = 0.0366$.

✔ *Checker: Exact scipy $z = -2.0851, p = 0.037056$.*

---

### Exercise 11.10
**Problem:** GfK Custom Research North America conducted identical surveys five years apart. One question asked of women was "Are most men basically kind, gentle, and thoughtful?" The earlier survey revealed that, of the 3,000 women surveyed, 2,010 said that they were. The later revealed 1,530 of the 3,000 women surveyed thought that men were kind, gentle, and thoughtful. At the .05 level, can we conclude that women think men are less kind, gentle, and thoughtful in the later survey compared with the earlier one?

**Given:** $n_1 = 3000, X_1 = 2010$ ($p_1 = 0.6700$); $n_2 = 3000, X_2 = 1530$ ($p_2 = 0.5100$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{2010 + 1530}{3000 + 3000} = \frac{3540}{6000} = 0.5900$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.6700 - 0.5100}{0.0127} = 12.60$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 12.60$), $p\text{-value} = 0.0000$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.5900$; Reject $H_0$ if $z > 1.65$.; $z = 12.60$; Reject $H_0$; $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 12.5993, p = 0.000000$.*

---

### Exercise 11.11
**Problem:** A nationwide sample of influential Republicans and Democrats was asked as a part of a comprehensive survey whether they favored lowering environmental standards so that high-sulfur coal could be burned in coal-fired power plants. The results were: Republicans ($n_r = 1,000$, number in favor $= 200$) and Democrats ($n_d = 800$, number in favor $= 168$). At the .02 level of significance, can we conclude that there is a larger proportion of Democrats in favor of lowering the standards? Determine the p-value.

**Given:** $n_1 = 800, X_1 = 168$ ($p_1 = 0.2100$); $n_2 = 1000, X_2 = 200$ ($p_2 = 0.2000$); $\alpha = 0.02$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 2.05$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{168 + 200}{800 + 1000} = \frac{368}{1800} = 0.2044$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.2100 - 0.2000}{0.0191} = 0.52$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 0.52$), $p\text{-value} = 0.3015$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.05$).*

**Answer:** $p_c = 0.2044$; Reject $H_0$ if $z > 2.05$.; $z = 0.52$; Do not reject $H_0$; $p\text{-value} = 0.3015$.

✔ *Checker: Exact scipy $z = 0.5227, p = 0.300578$.*

---

### Exercise 11.12
**Problem:** The research department at the home office of New Hampshire Insurance conducts ongoing research on the causes of automobile accidents, the characteristics of the drivers, and so on. A random sample of 400 policies written on single persons revealed 120 had at least one accident in the previous three-year period. Similarly, a sample of 600 policies written on married persons revealed that 150 had been in at least one accident. At the .05 significance level, is there a significant difference in the proportions of single and married persons having an accident during a three-year period? Determine the p-value.

**Given:** $n_1 = 400, X_1 = 120$ ($p_1 = 0.3000$); $n_2 = 600, X_2 = 150$ ($p_2 = 0.2500$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Pooled proportion:**
$$p_c = \frac{X_1 + X_2}{n_1 + n_2} = \frac{120 + 150}{400 + 600} = \frac{270}{1000} = 0.2700$$
- **Test statistic:**
$$z = \frac{p_1 - p_2}{\sqrt{p_c(1-p_c)/n_1 + p_c(1-p_c)/n_2}} = \frac{0.3000 - 0.2500}{0.0287} = 1.74$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.74$), $p\text{-value} = 0.0818$.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $p_c = 0.2700$; Reject $H_0$ if $z < -1.96$ or $z > 1.96$.; $z = 1.74$; Do not reject $H_0$; $p\text{-value} = 0.0818$.

✔ *Checker: Exact scipy $z = 1.7447, p = 0.081029$.*

---

## Lind — Chapter 11, Section 11.4: Independent Samples ($\sigma_1$ and $\sigma_2$ Unknown)

### Exercise 11.13
**Problem:** The null and alternate hypotheses are: $H_0: \mu_1 = \mu_2$ and $H_1: \mu_1 \neq \mu_2$. A random sample of 10 observations from one population revealed a sample mean of 23 and a sample deviation of 4. A random sample of 8 observations from another population revealed a sample mean of 26 and a sample standard deviation of 5. At the .05 significance level, is there a difference between the population means?

**Given:** $n_1 = 10, \bar{X}_1 = 23.000, s_1 = 4.000$; $n_2 = 8, \bar{X}_2 = 26.000, s_2 = 5.000$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if $t < -2.120$ or $t > 2.120$ ($df = 16, \alpha = 0.05$).
- **Pooled variance:**
$$s_p^2 = \frac{(10-1)(4.000)^2 + (8-1)(5.000)^2}{10+8-2} = 19.9375$$
- **Test statistic:**
$$t = \frac{23.000 - 26.000}{\sqrt{19.9375(1/10 + 1/8)}} = -1.416$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.1758$.

📘 *Table used: Lind Appendix B.2 ($df = 16, t_{\text{crit}} = 2.120$).*

**Answer:** $s_p^2 = 19.9375, t = -1.416$; Do not reject $H_0$; $p\text{-value} = 0.1758$.

✔ *Checker: Exact scipy $t = -1.4164, p = 0.175825$.*

---

### Exercise 11.14
**Problem:** The null and alternate hypotheses are: $H_0: \mu_1 = \mu_2$ and $H_1: \mu_1 \neq \mu_2$. A random sample of 15 observations from the first population revealed a sample mean of 350 and a sample standard deviation of 12. A random sample of 17 observations from the second population revealed a sample mean of 342 and a sample standard deviation of 15. At the .10 significance level, is there a difference in the population means?

**Given:** $n_1 = 15, \bar{X}_1 = 350.000, s_1 = 12.000$; $n_2 = 17, \bar{X}_2 = 342.000, s_2 = 15.000$; $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if $t < -1.697$ or $t > 1.697$ ($df = 30, \alpha = 0.1$).
- **Pooled variance:**
$$s_p^2 = \frac{(15-1)(12.000)^2 + (17-1)(15.000)^2}{15+17-2} = 187.2000$$
- **Test statistic:**
$$t = \frac{350.000 - 342.000}{\sqrt{187.2000(1/15 + 1/17)}} = 1.651$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.1093$.

📘 *Table used: Lind Appendix B.2 ($df = 30, t_{\text{crit}} = 1.697$).*

**Answer:** $s_p^2 = 187.2000, t = 1.651$; Do not reject $H_0$; $p\text{-value} = 0.1093$.

✔ *Checker: Exact scipy $t = 1.6506, p = 0.109260$.*

---

### Exercise 11.15
**Problem:** Listed in the text are the salaries in $000 of the 25 players on the opening-day roster of the 2010 New York Yankees Major League baseball team. Sort the players into two groups, pitchers ($n_1=12$) and nonpitchers/position players ($n_2=13$). Assume equal population variances for the position players and the pitchers. Test the hypothesis that mean salaries between position players and pitchers are the same versus the alternate hypothesis that they are not the same. Use the .01 significance level.

**Given:** $n_1 = 12, \bar{X}_1 = 7240.258, s_1 = 8242.208$; $n_2 = 13, \bar{X}_2 = 9188.492, s_2 = 10368.933$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if $t < -2.807$ or $t > 2.807$ ($df = 23, \alpha = 0.01$).
- **Pooled variance:**
$$s_p^2 = \frac{(12-1)(8242.208)^2 + (13-1)(10368.933)^2}{12+13-2} = 88584842.5573$$
- **Test statistic:**
$$t = \frac{7240.258 - 9188.492}{\sqrt{88584842.5573(1/12 + 1/13)}} = -0.517$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.6100$.

📘 *Table used: Lind Appendix B.2 ($df = 23, t_{\text{crit}} = 2.807$).*

**Answer:** $s_p^2 = 88584842.5573, t = -0.517$; Do not reject $H_0$; $p\text{-value} = 0.6100$.

✔ *Checker: Exact scipy $t = -0.5171, p = 0.610041$.*

---

### Exercise 11.16
**Problem:** A recent study compared the time spent together by single- and dual-earner couples. According to the records kept by the wives during the study, the mean amount of time spent together watching television among the single-earner couples was 61 minutes per day, with a standard deviation of 15.5 minutes. For the dual-earner couples, the mean number of minutes spent watching television was 48.4 minutes, with a standard deviation of 18.1 minutes. At the .01 significance level, can we conclude that the single-earner couples on average spend more time watching television together? There were 15 single-earner and 12 dual-earner couples studied.

**Given:** $n_1 = 15, \bar{X}_1 = 61.000, s_1 = 15.500$; $n_2 = 12, \bar{X}_2 = 48.400, s_2 = 18.100$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 2.485$ ($df = 25, \alpha = 0.01$).
- **Pooled variance:**
$$s_p^2 = \frac{(15-1)(15.500)^2 + (12-1)(18.100)^2}{15+12-2} = 278.6884$$
- **Test statistic:**
$$t = \frac{61.000 - 48.400}{\sqrt{278.6884(1/15 + 1/12)}} = 1.949$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.0313$.

📘 *Table used: Lind Appendix B.2 ($df = 25, t_{\text{crit}} = 2.485$).*

**Answer:** $s_p^2 = 278.6884, t = 1.949$; Do not reject $H_0$; $p\text{-value} = 0.0313$.

✔ *Checker: Exact scipy $t = 1.9488, p = 0.031314$.*

---

### Exercise 11.17
**Problem:** Ms. Lisa Monnin is the budget director for Nexus Media Inc. She would like to compare the daily travel expenses for the sales staff (`131, 135, 146, 165, 136, 142`) and the audit staff (`130, 102, 129, 143, 149, 120, 139`). At the .10 significance level, can she conclude that the mean daily expenses are greater for the sales staff than the audit staff? What is the p-value?

**Given:** $n_1 = 6, \bar{X}_1 = 142.500, s_1 = 12.243$; $n_2 = 7, \bar{X}_2 = 130.286, s_2 = 15.787$; $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 1.363$ ($df = 11, \alpha = 0.1$).
- **Pooled variance:**
$$s_p^2 = \frac{(6-1)(12.243)^2 + (7-1)(15.787)^2}{6+7-2} = 204.0844$$
- **Test statistic:**
$$t = \frac{142.500 - 130.286}{\sqrt{204.0844(1/6 + 1/7)}} = 1.537$$
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0763$.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 1.363$).*

**Answer:** $s_p^2 = 204.0844, t = 1.537$; Reject $H_0$; $p\text{-value} = 0.0763$.

✔ *Checker: Exact scipy $t = 1.5368, p = 0.076297$.*

---

### Exercise 11.18
**Problem:** The Tampa Bay (Florida) Area Chamber of Commerce wanted to know whether the mean weekly salary of nurses (`841, 890, 821, 771, 850, 859, 825, 829`) was larger than that of school teachers (`845, 826, 827, 875, 784, 809, 802, 820, 829, 830, 842, 832`). Is it reasonable to conclude that the mean weekly salary of nurses is higher? Use the .01 significance level. What is the p-value?

**Given:** $n_1 = 8, \bar{X}_1 = 835.750, s_1 = 34.404$; $n_2 = 12, \bar{X}_2 = 826.750, s_2 = 22.840$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 2.552$ ($df = 18, \alpha = 0.01$).
- **Pooled variance:**
$$s_p^2 = \frac{(8-1)(34.404)^2 + (12-1)(22.840)^2}{8+12-2} = 779.0972$$
- **Test statistic:**
$$t = \frac{835.750 - 826.750}{\sqrt{779.0972(1/8 + 1/12)}} = 0.706$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.2445$.

📘 *Table used: Lind Appendix B.2 ($df = 18, t_{\text{crit}} = 2.552$).*

**Answer:** $s_p^2 = 779.0972, t = 0.706$; Do not reject $H_0$; $p\text{-value} = 0.2445$.

✔ *Checker: Exact scipy $t = 0.7064, p = 0.244483$.*

---

### Exercise 11.19
**Problem:** Assume the sample populations do not have equal standard deviations and use the .05 significance level: $H_0: \mu_1 = \mu_2$ and $H_1: \mu_1 \neq \mu_2$. A random sample of 15 items from the first population showed a mean of 50 and a standard deviation of 5. A sample of 12 items for the second population showed a mean of 46 and a standard deviation of 15.
(a) Determine the number of degrees of freedom.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) State your decision about the null hypothesis.

**Given:** $n_1 = 15, \bar{X}_1 = 50.000, s_1 = 5.0000$; $n_2 = 12, \bar{X}_2 = 46.000, s_2 = 15.0000$; $\alpha = 0.05$ (unequal variances).

- **Degrees of freedom [11–8]:**
$$df = \frac{(s_1^2/n_1 + s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}} = 12.96 \implies \mathbf{12} \text{ (rounded down)}$$
- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if $t < -2.179$ or $t > 2.179$ ($df = 12, \alpha = 0.05$).
- **Test statistic [11–7]:**
$$t = \frac{50.000 - 46.000}{\sqrt{5.0000^2/15 + 15.0000^2/12}} = \frac{4.000}{4.5185} = 0.885$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.2 ($df = 12, t_{\text{crit}} = 2.179$).*

**Answer:** $df = 12$ (from $12.96$); Reject $H_0$ if $t < -2.179$ or $t > 2.179$ ($df = 12, \alpha = 0.05$).; $t = 0.885$; Do not reject $H_0$.

✔ *Checker: Exact scipy Welch $t = 0.8853, p = 0.393413$.*

---

### Exercise 11.20
**Problem:** Assume the sample populations do not have equal standard deviations and use the .05 significance level: $H_0: \mu_1 \le \mu_2$ and $H_1: \mu_1 > \mu_2$. A random sample of 20 items from the first population showed a mean of 100 and a standard deviation of 15. A sample of 16 items for the second population showed a mean of 94 and a standard deviation of 8.
(a) Determine the number of degrees of freedom.
(b) State the decision rule.
(c) Compute the value of the test statistic.
(d) State your decision about the null hypothesis.

**Given:** $n_1 = 20, \bar{X}_1 = 100.000, s_1 = 15.0000$; $n_2 = 16, \bar{X}_2 = 94.000, s_2 = 8.0000$; $\alpha = 0.05$ (unequal variances).

- **Degrees of freedom [11–8]:**
$$df = \frac{(s_1^2/n_1 + s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}} = 30.09 \implies \mathbf{30} \text{ (rounded down)}$$
- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 1.701$ ($df = 30, \alpha = 0.05$).
- **Test statistic [11–7]:**
$$t = \frac{100.000 - 94.000}{\sqrt{15.0000^2/20 + 8.0000^2/16}} = \frac{6.000}{3.9051} = 1.536$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.2 ($df = 30, t_{\text{crit}} = 1.701$).*

**Answer:** $df = 30$ (from $30.09$); Reject $H_0$ if $t > 1.701$ ($df = 30, \alpha = 0.05$).; $t = 1.536$; Do not reject $H_0$.

✔ *Checker: Exact scipy Welch $t = 1.5364, p = 0.067455$.*

---

### Exercise 11.21
**Problem:** A recent article in The Wall Street Journal compared the cost of adopting children from China with that of Russia. For a sample of 16 adoptions from China, the mean cost was $11,045, with a standard deviation of $835. For a sample of 18 adoptions from Russia, the mean cost was $12,840, with a standard deviation of $1,545. Can we conclude the mean cost is larger for adopting children from Russia? Assume the two population standard deviations are not the same. Use the .05 significance level.

**Given:** $n_1 = 18, \bar{X}_1 = 12840.000, s_1 = 1545.0000$; $n_2 = 16, \bar{X}_2 = 11045.000, s_2 = 835.0000$; $\alpha = 0.05$ (unequal variances).

- **Degrees of freedom [11–8]:**
$$df = \frac{(s_1^2/n_1 + s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}} = 26.74 \implies \mathbf{26} \text{ (rounded down)}$$
- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 1.706$ ($df = 26, \alpha = 0.05$).
- **Test statistic [11–7]:**
$$t = \frac{12840.000 - 11045.000}{\sqrt{1545.0000^2/18 + 835.0000^2/16}} = \frac{1795.000}{419.7488} = 4.276$$
- **Decision:** **Reject $H_0$**.

📘 *Table used: Lind Appendix B.2 ($df = 26, t_{\text{crit}} = 1.706$).*

**Answer:** $df = 26$ (from $26.74$); Reject $H_0$ if $t > 1.706$ ($df = 26, \alpha = 0.05$).; $t = 4.276$; Reject $H_0$.

✔ *Checker: Exact scipy Welch $t = 4.2764, p = 0.000113$.*

---

### Exercise 11.22
**Problem:** Suppose you are an expert on the fashion industry and wish to gather information to compare the amount earned per month by models featuring Liz Claiborne attire (`5.0, 4.5, 3.4, 3.4, 6.0, 3.3, 4.5, 4.6, 3.5, 5.2, 4.8, 4.4, 4.6, 3.6, 5.0`) with those of Calvin Klein (`3.1, 3.7, 3.6, 4.0, 3.8, 3.8, 5.9, 4.9, 3.6, 3.6, 2.3, 4.0`). Is it reasonable to conclude that Claiborne models earn more? Use the .05 significance level and assume the population standard deviations are not the same.

**Given:** $n_1 = 15, \bar{X}_1 = 4.387, s_1 = 0.7945$; $n_2 = 12, \bar{X}_2 = 3.858, s_2 = 0.8806$; $\alpha = 0.05$ (unequal variances).

- **Degrees of freedom [11–8]:**
$$df = \frac{(s_1^2/n_1 + s_2^2/n_2)^2}{\frac{(s_1^2/n_1)^2}{n_1-1} + \frac{(s_2^2/n_2)^2}{n_2-1}} = 22.50 \implies \mathbf{22} \text{ (rounded down)}$$
- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 1.714$ ($df = 22, \alpha = 0.05$).
- **Test statistic [11–7]:**
$$t = \frac{4.387 - 3.858}{\sqrt{0.7945^2/15 + 0.8806^2/12}} = \frac{0.528}{0.3266} = 1.617$$
- **Decision:** **Do not reject $H_0$**.

📘 *Table used: Lind Appendix B.2 ($df = 22, t_{\text{crit}} = 1.714$).*

**Answer:** $df = 22$ (from $22.50$); Reject $H_0$ if $t > 1.714$ ($df = 22, \alpha = 0.05$).; $t = 1.617$; Do not reject $H_0$.

✔ *Checker: Exact scipy Welch $t = 1.6175, p = 0.060015$.*

---

## Lind — Chapter 11, Sections 11.5–11.6: Dependent (Paired) Samples

### Exercise 11.23
**Problem:** The null and alternate hypotheses are: $H_0: \mu_d \le 0$ and $H_1: \mu_d > 0$. The following sample information shows the number of defective units produced on the day shift (`10, 12, 15, 19`) and the afternoon shift (`8, 9, 12, 15`) for a sample of four days last month. At the .05 significance level, can we conclude there are more defects produced on the day shift (defining $d = \text{Day} - \text{Afternoon}$)?

**Given:** $n = 4$ pairs ($df = 3$), differences $d = [2, 3, 3, 4]$, $\alpha = 0.05$.

- **Sample difference statistics:** $\bar{d} = 3.000$, $s_d = 0.816$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule:** Reject $H_0$ if $t > 2.353$ ($df = 3, \alpha = 0.05$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{3.000}{0.816 / \sqrt{4}} = 7.348$$
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0026$.

📘 *Table used: Lind Appendix B.2 ($df = 3, t_{\text{crit}} = 2.353$).*

**Answer:** $\bar{d} = 3.000, s_d = 0.816, t = 7.348$; Reject $H_0$; $p\text{-value} = 0.0026$.

✔ *Checker: Exact scipy $t = 7.3485, p = 0.002604$.*

---

### Exercise 11.24
**Problem:** The null and alternate hypotheses are: $H_0: \mu_d = 0$ and $H_1: \mu_d \neq 0$. The following paired observations show the number of traffic citations given for speeding by Officer Dhondt (`30, 22, 25, 19, 26`) and Officer Meredith (`26, 19, 20, 15, 19`) of the South Carolina Highway Patrol for the last five months. At the .05 significance level, is there a difference in the mean number of citations given by the two officers?

**Given:** $n = 5$ pairs ($df = 4$), differences $d = [4, 3, 5, 4, 7]$, $\alpha = 0.05$.

- **Sample difference statistics:** $\bar{d} = 4.600$, $s_d = 1.517$.
- **Hypotheses:** $H_0: \mu_d = 0$ versus $H_1: \mu_d \neq 0$.
- **Decision rule:** Reject $H_0$ if $t < -2.776$ or $t > 2.776$ ($df = 4, \alpha = 0.05$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{4.600}{1.517 / \sqrt{5}} = 6.782$$
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0025$.

📘 *Table used: Lind Appendix B.2 ($df = 4, t_{\text{crit}} = 2.776$).*

**Answer:** $\bar{d} = 4.600, s_d = 1.517, t = 6.782$; Reject $H_0$; $p\text{-value} = 0.0025$.

✔ *Checker: Exact scipy $t = 6.7823, p = 0.002467$.*

---

### Exercise 11.25
**Problem:** The management of Discount Furniture, a chain of discount furniture stores in the Northeast, designed an incentive plan for salespeople. To evaluate this innovative plan, 12 salespeople were selected at random, and their weekly incomes before (`320, 290, 421, 510, 210, 402, 625, 560, 360, 431, 506, 505`) and after (`340, 285, 475, 510, 210, 500, 631, 560, 365, 431, 525, 619`) the plan were recorded. Was there a significant increase in the typical salesperson's weekly income due to the innovative incentive plan? Use the .05 significance level. Estimate the p-value, and interpret it.

**Given:** $n = 12$ pairs ($df = 11$), differences $d = [20, -5, 54, 0, 0, 98, 6, 0, 5, 0, 19, 114]$, $\alpha = 0.05$.

- **Sample difference statistics:** $\bar{d} = 25.917$, $s_d = 40.791$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule:** Reject $H_0$ if $t > 1.796$ ($df = 11, \alpha = 0.05$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{25.917}{40.791 / \sqrt{12}} = 2.201$$
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0250$.

📘 *Table used: Lind Appendix B.2 ($df = 11, t_{\text{crit}} = 1.796$).*

**Answer:** $\bar{d} = 25.917, s_d = 40.791, t = 2.201$; Reject $H_0$; $p\text{-value} = 0.0250$.

✔ *Checker: Exact scipy $t = 2.2009, p = 0.025002$.*

---

### Exercise 11.26
**Problem:** The federal government recently granted funds for a special program designed to reduce crime in high-crime areas. A study of the results of the program in eight high-crime areas of Miami, Florida, yielded the following number of crimes Before (`14, 7, 4, 5, 17, 12, 8, 9`) and After (`2, 7, 3, 6, 8, 13, 3, 5`). Has there been a decrease in the number of crimes since the inauguration of the program? Use the .01 significance level. Estimate the p-value.

**Given:** $n = 8$ pairs ($df = 7$), differences $d = [12, 0, 1, -1, 9, -1, 5, 4]$, $\alpha = 0.01$.

- **Sample difference statistics:** $\bar{d} = 3.625$, $s_d = 4.838$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule:** Reject $H_0$ if $t > 2.998$ ($df = 7, \alpha = 0.01$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{3.625}{4.838 / \sqrt{8}} = 2.119$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.0359$.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = 2.998$).*

**Answer:** $\bar{d} = 3.625, s_d = 4.838, t = 2.119$; Do not reject $H_0$; $p\text{-value} = 0.0359$.

✔ *Checker: Exact scipy $t = 2.1191, p = 0.035910$.*

---

## Lind — Chapter 11: Chapter Exercises

### Exercise 11.27
**Problem:** A recent study focused on the number of times men ($n_1=35, \bar{X}_1=24.51, \sigma_1=4.48$) and women ($n_2=40, \bar{X}_2=22.69, \sigma_2=3.86$) who live alone buy take-out dinner in a month. At the .01 significance level, is there a difference in the mean number of times men and women order take-out dinners in a month? What is the p-value?

**Given:** Men: $n_1 = 35, \bar{X}_1 = 24.51, \sigma_1 = 4.48$; Women: $n_2 = 40, \bar{X}_2 = 22.69, \sigma_2 = 3.86$; $\alpha = .01$.

- **Hypotheses:** $H_0: \mu_M = \mu_W$ versus $H_1: \mu_M \neq \mu_W$.
- **Decision rule:** Using $z$ ($\sigma$ known): reject $H_0$ if $z < -2.58$ or $z > 2.58$. (Using pooled $t$ with $df = 73$ as in Appendix C: reject $H_0$ if $t < -2.645$ or $t > 2.645$.)
- **Test statistic:**
  - Using formula [11–2] ($\sigma$ known):
  $$z = \frac{24.51 - 22.69}{\sqrt{4.48^2/35 + 3.86^2/40}} = \frac{1.82}{0.9726} = 1.87, \qquad p\text{-value} = 2(.5000 - .4693) = .0614$$
  - Using pooled $t$ [11–6] (Appendix C): $s_p^2 = \frac{34(4.48)^2 + 39(3.86)^2}{73} = 17.3079$, $t = \frac{1.82}{\sqrt{17.3079(1/35 + 1/40)}} = 1.890$ ($p$-value between $.05$ and $.10$).
- **Decision:** **Do not reject $H_0$**. There is no significant difference at the .01 level.

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** $z = 1.87$ ($p = .0614$) or pooled $t = 1.890$ ($p$ between $.05$ and $.10$); do not reject $H_0$.

✔ *Checker: Matches both formula [11–2] ($z = 1.8712$) and Appendix C ($t = 1.890$).*

---

### Exercise 11.28
**Problem:** Clark Heter is an industrial engineer at Lyons Products. He would like to determine whether there are more units produced on the night shift than on the day shift. Assume the population standard deviation for the number of units produced on the day shift is 21 and is 28 on the night shift. A sample of 54 day-shift workers showed that the mean number of units produced was 345. A sample of 60 night-shift workers showed that the mean number of units produced was 351. At the .05 significance level, is the number of units produced on the night shift larger?

**Given:** $n_1 = 60, \bar{X}_1 = 351.0, s_1 = 28.0$; $n_2 = 54, \bar{X}_2 = 345.0, s_2 = 21.0$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if test statistic $> 1.65$.
- **Test statistic:**
$$\frac{351.0 - 345.0}{\sqrt{28.0^2/60 + 21.0^2/54}} = \frac{6.00}{4.6080} = 1.30$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.30$), $p\text{-value} = 0.0968$.

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** Test statistic $= 1.30$; Do not reject $H_0$; $p\text{-value} = 0.0968$.

✔ *Checker: Exact scipy value $= 1.3021$.*

---

### Exercise 11.29
**Problem:** Fry Brothers Heating and Air Conditioning Inc. employs Larry Clark and George Murnen to make service calls to repair furnaces and air conditioning units in homes. Tom Fry, the owner, would like to know whether there is a difference in the mean number of service calls they make per day. Assume the population standard deviation for Larry Clark is 1.05 calls per day and 1.23 calls per day for George Murnen. A random sample of 40 days last year showed that Larry Clark made an average of 4.77 calls per day. For a sample of 50 days George Murnen made an average of 5.02 calls per day. At the .05 significance level, is there a difference in the mean number of calls per day between the two employees? What is the p-value?

**Given:** $n_1 = 40, \bar{X}_1 = 4.77, s_1 = 1.05$; $n_2 = 50, \bar{X}_2 = 5.02, s_2 = 1.23$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if test statistic $< -1.96$ or $> 1.96$.
- **Test statistic:**
$$\frac{4.77 - 5.02}{\sqrt{1.05^2/40 + 1.23^2/50}} = \frac{-0.25}{0.2405} = -1.04$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -1.04$), $p\text{-value} = 0.2984$.

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** Test statistic $= -1.04$; Do not reject $H_0$; $p\text{-value} = 0.2984$.

✔ *Checker: Exact scipy value $= -1.0397$.*

---

### Exercise 11.30
**Problem:** A coffee manufacturer is interested in whether the mean daily consumption of regular-coffee drinkers is less than that of decaffeinated-coffee drinkers. Assume the population standard deviation for those drinking regular coffee is 1.20 cups per day and 1.36 cups per day for those drinking decaffeinated coffee. A random sample of 50 regular-coffee drinkers showed a mean of 4.35 cups per day. A sample of 40 decaffeinated-coffee drinkers showed a mean of 5.84 cups per day. Use the .01 significance level. Compute the p-value.

**Given:** $n_1 = 50, \bar{X}_1 = 4.35, s_1 = 1.2$; $n_2 = 40, \bar{X}_2 = 5.84, s_2 = 1.36$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 \ge \mu_2$ versus $H_1: \mu_1 < \mu_2$.
- **Decision rule:** Reject $H_0$ if test statistic $< -2.33$.
- **Test statistic:**
$$\frac{4.35 - 5.84}{\sqrt{1.2^2/50 + 1.36^2/40}} = \frac{-1.49}{0.2739} = -5.44$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -5.44$), $p\text{-value} = 0.0000$.

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** Test statistic $= -5.44$; Reject $H_0$; $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy value $= -5.4393$.*

---

### Exercise 11.31
**Problem:** A cell phone company offers two plans to its subscribers. The mean yearly income for a sample of 40 subscribers to Plan A is $57,000 with a standard deviation of $9,200 (skewness 2.11). For a sample of 30 subscribers to Plan B, the mean income is $61,000 with a standard deviation of $7,100 (skewness 1.54). At the .05 significance level, is it reasonable to conclude the mean income of those selecting Plan B is larger? What is the p-value? Do the coefficients of skewness affect the results of the hypothesis test? Why?

**Given:** $n_1 = 30, \bar{X}_1 = 61000.0, s_1 = 7100.0$; $n_2 = 40, \bar{X}_2 = 57000.0, s_2 = 9200.0$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if test statistic $> 1.67$.
- **Test statistic:**
$$\frac{61000.0 - 57000.0}{\sqrt{7100.0^2/30 + 9200.0^2/40}} = \frac{4000.00}{1948.4182} = 2.05$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.05$), $p\text{-value} = 0.0202$.
- **Skewness note:** By the Central Limit Theorem, because both sample sizes are at least 30 ($n_1 = 30, n_2 = 40$), the sampling distribution of the difference between sample means is approximately normal regardless of population skewness.

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** Test statistic $= 2.05$; Reject $H_0$; $p\text{-value} = 0.0202$.

✔ *Checker: Exact scipy value $= 2.0529$.*

---

### Exercise 11.32
**Problem:** A computer manufacturer offers a help line that purchasers can call for help 24 hours a day, 7 days a week. The mean time it takes a technician to resolve a software issue is 18 minutes with a standard deviation of 4.2 minutes ($n_1=35$). For a study of 45 hardware issues, the mean time for the technician to resolve the problem was 15.5 minutes with a standard deviation of 3.9 minutes ($n_2=45$). At the .05 significance level, does it take longer to resolve software issues? What is the p-value?

**Given:** $n_1 = 35, \bar{X}_1 = 18.0, s_1 = 4.2$; $n_2 = 45, \bar{X}_2 = 15.5, s_2 = 3.9$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if test statistic $> 1.67$.
- **Test statistic:**
$$\frac{18.0 - 15.5}{\sqrt{4.2^2/35 + 3.9^2/45}} = \frac{2.50}{0.9176} = 2.72$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 2.72$), $p\text{-value} = 0.0033$.
- *(Note: Using pooled $t$ with $df = 78$, $s_p^2 = 16.2692$ and $t = 2.750 > 1.665$, giving the same decision: reject $H_0$, $p = 0.0037$.)*

📘 *Table used: Lind Appendix B.1 / B.2.*

**Answer:** Test statistic $= 2.72$; Reject $H_0$; $p\text{-value} = 0.0033$.

✔ *Checker: Exact scipy value $= 2.7245$.*

---

### Exercise 11.33
**Problem:** Suppose the manufacturer of Advil, a common headache remedy, recently developed a new formulation of the drug that is claimed to be more effective. To evaluate the new drug, a sample of 200 current users is asked to try it. After a one-month trial, 180 indicated the new drug was more effective in relieving a headache. At the same time, a sample of 300 current Advil users is given the current drug but told it is the new formulation. From this group, 261 said it was an improvement. At the .05 significance level, can we conclude that the new drug is more effective?

**Given:** $n_1 = 200, X_1 = 180$ ($p_1 = 0.9000$); $n_2 = 300, X_2 = 261$ ($p_2 = 0.8700$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:** $p_c = \frac{180+261}{200+300} = 0.8820$.
- **Test statistic:**
$$z = \frac{0.9000 - 0.8700}{\sqrt{0.8820(0.1180)(1/200 + 1/300)}} = \frac{0.0300}{0.0294} = 1.019$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.02$), $p\text{-value} = 0.1539$ (exact $p = 0.1542$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.8820, z = 1.019$; Do not reject $H_0$; $p\text{-value} = 0.1539$.

✔ *Checker: Exact scipy $z = 1.0187, p = 0.154178$.*

---

### Exercise 11.34
**Problem:** Each month the National Association of Purchasing Managers publishes the NAPM index. One of the questions asked on the survey to purchasing agents is: Do you think the economy is contracting? Last month, of the 300 responses, 160 answered yes to the question. This month, 170 of the 290 responses indicated they felt the economy was contracting. At the .05 significance level, can we conclude that a larger proportion of the agents believe the economy is contracting this month?

**Given:** $n_1 = 290, X_1 = 170$ ($p_1 = 0.5862$); $n_2 = 300, X_2 = 160$ ($p_2 = 0.5333$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:** $p_c = \frac{170+160}{290+300} = 0.5593$.
- **Test statistic:**
$$z = \frac{0.5862 - 0.5333}{\sqrt{0.5593(0.4407)(1/290 + 1/300)}} = \frac{0.0529}{0.0409} = 1.293$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.29$), $p\text{-value} = 0.0985$ (exact $p = 0.0980$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.5593, z = 1.293$; Do not reject $H_0$; $p\text{-value} = 0.0985$.

✔ *Checker: Exact scipy $z = 1.2932, p = 0.097963$.*

---

### Exercise 11.35
**Problem:** As part of a recent survey among dual-wage-earner couples, an industrial psychologist found that 990 men out of the 1,500 surveyed believed the division of household duties was fair. A sample of 1,600 women found 970 believed the division of household duties was fair. At the .01 significance level, is it reasonable to conclude that the proportion of men who believe the division of household duties is fair is larger? What is the p-value?

**Given:** $n_1 = 1500, X_1 = 990$ ($p_1 = 0.6600$); $n_2 = 1600, X_2 = 970$ ($p_2 = 0.6062$); $\alpha = 0.01$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 2.33$.
- **Pooled proportion:** $p_c = \frac{990+970}{1500+1600} = 0.6323$.
- **Test statistic:**
$$z = \frac{0.6600 - 0.6062}{\sqrt{0.6323(0.3677)(1/1500 + 1/1600)}} = \frac{0.0538}{0.0173} = 3.102$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 3.10$), $p\text{-value} = 0.0000$ (exact $p = 0.0010$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33$).*

**Answer:** $p_c = 0.6323, z = 3.102$; Reject $H_0$; $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 3.1016, p = 0.000962$.*

---

### Exercise 11.36
**Problem:** There are two major Internet providers in the Colorado Springs, Colorado, area, one called HTC and the other Mountain Communications. During a one-week period, 500 calls were placed at random times throughout the day and night to HTC ($X_1 = 450$ connections). A similar one-week study with Mountain Communications showed the Internet to be available on 352 of 400 trials. At the .01 significance level, is there a difference in the percent of time that access to the Internet is successful?

**Given:** $n_1 = 500, X_1 = 450$ ($p_1 = 0.9000$); $n_2 = 400, X_2 = 352$ ($p_2 = 0.8800$); $\alpha = 0.01$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -2.58$ or $z > 2.58$.
- **Pooled proportion:** $p_c = \frac{450+352}{500+400} = 0.8911$.
- **Test statistic:**
$$z = \frac{0.9000 - 0.8800}{\sqrt{0.8911(0.1089)(1/500 + 1/400)}} = \frac{0.0200}{0.0209} = 0.957$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 0.96$), $p\text{-value} = 0.3370$ (exact $p = 0.3385$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.58$).*

**Answer:** $p_c = 0.8911, z = 0.957$; Do not reject $H_0$; $p\text{-value} = 0.3370$.

✔ *Checker: Exact scipy $z = 0.9571, p = 0.338507$.*

---

### Exercise 11.37
**Problem:** The Consumer Confidence Survey is a monthly review that measures consumer confidence in the U.S. economy. It is based on a typical sample of 5,000 U.S. households. Last month 9.1 percent of consumers said conditions were "good." In the prior month, only 8.5 percent held they were "good." Use the five-step hypothesis-testing method at the .05 level of significance to see whether you can determine there is an increase in the share asserting conditions are "good." Find the p-value and explain what it means.

**Given:** $n_1 = 5000, X_1 = 455$ ($p_1 = 0.0910$); $n_2 = 5000, X_2 = 425$ ($p_2 = 0.0850$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:** $p_c = \frac{455+425}{5000+5000} = 0.0880$.
- **Test statistic:**
$$z = \frac{0.0910 - 0.0850}{\sqrt{0.0880(0.9120)(1/5000 + 1/5000)}} = \frac{0.0060}{0.0057} = 1.059$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 1.06$), $p\text{-value} = 0.1446$ (exact $p = 0.1448$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.0880, z = 1.059$; Do not reject $H_0$; $p\text{-value} = 0.1446$.

✔ *Checker: Exact scipy $z = 1.0590, p = 0.144807$.*

---

### Exercise 11.38
**Problem:** A study was conducted to determine if there was a difference in the humor content in British and American trade magazine advertisements. In an independent random sample of 270 American trade magazine advertisements, 56 were humorous. An independent random sample of 203 British trade magazines contained 52 humorous ads. Does this data provide evidence at the .05 significance level that there is a difference in the proportion of humorous ads in British versus American trade magazines?

**Given:** $n_1 = 270, X_1 = 56$ ($p_1 = 0.2074$); $n_2 = 203, X_2 = 52$ ($p_2 = 0.2562$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Pooled proportion:** $p_c = \frac{56+52}{270+203} = 0.2283$.
- **Test statistic:**
$$z = \frac{0.2074 - 0.2562}{\sqrt{0.2283(0.7717)(1/270 + 1/203)}} = \frac{-0.0488}{0.0390} = -1.250$$
- **Decision:** **Do not reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = -1.25$), $p\text{-value} = 0.2112$ (exact $p = 0.2112$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $p_c = 0.2283, z = -1.250$; Do not reject $H_0$; $p\text{-value} = 0.2112$.

✔ *Checker: Exact scipy $z = -1.2502, p = 0.211227$.*

---

### Exercise 11.39
**Problem:** The https://www.google.com/search?q=AP-Petside.com poll contacted 300 married women and 200 married men. All owned pets. One hundred of the women and 36 of the men replied that their pets are better listeners than their spouses. At the .05 significance level, is there a difference between the responses of women and men?

**Given:** $n_1 = 300, X_1 = 100$ ($p_1 = 0.3333$); $n_2 = 200, X_2 = 36$ ($p_2 = 0.1800$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$.
- **Decision rule:** Reject $H_0$ if $z < -1.96$ or $z > 1.96$.
- **Pooled proportion:** $p_c = \frac{100+36}{300+200} = 0.2720$.
- **Test statistic:**
$$z = \frac{0.3333 - 0.1800}{\sqrt{0.2720(0.7280)(1/300 + 1/200)}} = \frac{0.1533}{0.0406} = 3.775$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 3.77$), $p\text{-value} = 0.0000$ (exact $p = 0.0002$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.96$).*

**Answer:** $p_c = 0.2720, z = 3.775$; Reject $H_0$; $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 3.7747, p = 0.000160$.*

---

### Exercise 11.40
**Problem:** The National Basketball Association had 39 black top executives (presidents or vice presidents) among its 388 senior managers. Meanwhile, Major League Baseball had only 11 blacks among its 307 top administrators. Test at the .05 significance level if this reveals the NBA has significantly more black participation in higher levels of management.

**Given:** $n_1 = 388, X_1 = 39$ ($p_1 = 0.1005$); $n_2 = 307, X_2 = 11$ ($p_2 = 0.0358$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \pi_1 \le \pi_2$ versus $H_1: \pi_1 > \pi_2$.
- **Decision rule:** Reject $H_0$ if $z > 1.65$.
- **Pooled proportion:** $p_c = \frac{39+11}{388+307} = 0.0719$.
- **Test statistic:**
$$z = \frac{0.1005 - 0.0358}{\sqrt{0.0719(0.9281)(1/388 + 1/307)}} = \frac{0.0647}{0.0197} = 3.277$$
- **Decision:** **Reject $H_0$**.
- **$p$-value:** From Appendix B.1 ($z = 3.28$), $p\text{-value} = 0.0000$ (exact $p = 0.0005$).

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 1.65$).*

**Answer:** $p_c = 0.0719, z = 3.277$; Reject $H_0$; $p\text{-value} = 0.0000$.

✔ *Checker: Exact scipy $z = 3.2773, p = 0.000524$.*

---

### Exercise 11.41
**Problem:** Data gathered over the last 12 months show Apple's iTunes was used by an average of 1.65 million households with a sample standard deviation of 0.56 million family units. Over the same 12 months WinMX (a no-cost P2P download service) was used by an average of 2.2 million families with a sample standard deviation of 0.30 million. Assume the population standard deviations are not the same. Using a significance level of 0.05, test the hypothesis of no difference in the mean number of households picking either variety of service to download songs.

**Given:** $n_1 = 12, \bar{X}_1 = 1.650, s_1 = 0.5600$; $n_2 = 12, \bar{X}_2 = 2.200, s_2 = 0.3000$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Welch degrees of freedom [11–8]:** $df = 16.83 \implies 16$.
- **Decision rule:** Reject $H_0$ if $t < -2.120$ or $t > 2.120$ ($df = 16, \alpha = 0.05$).
- **Test statistic:** $t = \frac{1.650 - 2.200}{0.1834} = -2.999$.
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0085$.

📘 *Table used: Lind Appendix B.2 ($df = 16, t_{\text{crit}} = 2.120$).*

**Answer:** $\bar{X}_1 = 1.650, \bar{X}_2 = 2.200, df = 16, t = -2.999$; Reject $H_0$; $p\text{-value} = 0.0085$.

✔ *Checker: Exact scipy $t = -2.9990, p = 0.008497$.*

---

### Exercise 11.42
**Problem:** The sample of 35 e-coupon users had a mean age of 33.6 years with a standard deviation of 10.9, while a similar sample of 25 traditional paper-coupon clippers had a mean age of 39.5 with a standard deviation of 4.8. Assume the population standard deviations are not the same. Using a significance level of 0.01, test the hypothesis of no difference in the mean ages of the two groups of coupon clients.

**Given:** $n_1 = 35, \bar{X}_1 = 33.600, s_1 = 10.9000$; $n_2 = 25, \bar{X}_2 = 39.500, s_2 = 4.8000$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Welch degrees of freedom [11–8]:** $df = 49.77 \implies 49$.
- **Decision rule:** Reject $H_0$ if $t < -2.680$ or $t > 2.680$ ($df = 49, \alpha = 0.01$).
- **Test statistic:** $t = \frac{33.600 - 39.500}{2.0775} = -2.840$.
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0066$.

📘 *Table used: Lind Appendix B.2 ($df = 49, t_{\text{crit}} = 2.680$).*

**Answer:** $\bar{X}_1 = 33.600, \bar{X}_2 = 39.500, df = 49, t = -2.840$; Reject $H_0$; $p\text{-value} = 0.0066$.

✔ *Checker: Exact scipy $t = -2.8399, p = 0.006554$.*

---

### Exercise 11.43
**Problem:** The owner of Bun 'N' Run Hamburgers wishes to compare the sales per day at two locations. The mean number sold for 10 randomly selected days at the Northside site was 83.55, and the standard deviation was 10.50. For a random sample of 12 days at the Southside location, the mean number sold was 78.80 and the standard deviation was 14.25. At the .05 significance level, is there a difference in the mean number of hamburgers sold at the two locations? What is the p-value?

**Given:** $n_1 = 10, \bar{X}_1 = 83.550, s_1 = 10.5000$; $n_2 = 12, \bar{X}_2 = 78.800, s_2 = 14.2500$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Pooled variance [11–5]:** $s_p^2 = 161.2969$ ($df = 20$).
- **Decision rule:** Reject $H_0$ if $t < -2.086$ or $t > 2.086$ ($df = 20, \alpha = 0.05$).
- **Test statistic:** $t = \frac{83.550 - 78.800}{5.4379} = 0.873$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.3928$.

📘 *Table used: Lind Appendix B.2 ($df = 20, t_{\text{crit}} = 2.086$).*

**Answer:** $\bar{X}_1 = 83.550, \bar{X}_2 = 78.800, df = 20, t = 0.873$; Do not reject $H_0$; $p\text{-value} = 0.3928$.

✔ *Checker: Exact scipy $t = 0.8735, p = 0.392761$.*

---

### Exercise 11.44
**Problem:** The Engineering Department at Sims Software Inc. recently developed two chemical solutions designed to increase the usable life of computer disks. A sample of disks treated with the first solution lasted `86, 78, 66, 83, 84, 81, 84, 109, 65, 102` hours. Those treated with the second solution lasted `91, 71, 75, 76, 87, 79, 73, 76, 79, 78, 87, 90, 76, 72` hours. Assume the population standard deviations are not the same. At the .10 significance level, can we conclude that there is a difference in the length of time the two types of treatment lasted?

**Given:** $n_1 = 10, \bar{X}_1 = 83.800, s_1 = 13.6772$; $n_2 = 14, \bar{X}_2 = 79.286, s_2 = 6.7074$; $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Welch degrees of freedom [11–8]:** $df = 12.11 \implies 12$.
- **Decision rule:** Reject $H_0$ if $t < -1.796$ or $t > 1.796$ ($df = 12, \alpha = 0.1$).
- **Test statistic:** $t = \frac{83.800 - 79.286}{4.6819} = 0.964$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.3540$.

📘 *Table used: Lind Appendix B.2 ($df = 12, t_{\text{crit}} = 1.796$).*

**Answer:** $\bar{X}_1 = 83.800, \bar{X}_2 = 79.286, df = 12, t = 0.964$; Do not reject $H_0$; $p\text{-value} = 0.3540$.

✔ *Checker: Exact scipy $t = 0.9642, p = 0.353975$.*

---

### Exercise 11.45
**Problem:** The Willow Run Outlet Mall has two Haggar Outlet Stores, one located on Peach Street (`17.58, 19.73, 12.61, 17.79, 16.22, 15.82, 15.40, 15.86, 11.82, 15.85`) and the other on Plum Street (`18.19, 20.22, 17.38, 17.96, 23.92, 15.87, 16.47, 15.96, 16.79, 16.74, 21.40, 20.57, 19.79, 14.83`). At the .01 significance level, is there a difference in the mean amounts purchased on impulse at the two stores?

**Given:** $n_1 = 10, \bar{X}_1 = 15.868, s_1 = 2.3306$; $n_2 = 14, \bar{X}_2 = 18.292, s_2 = 2.5527$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Pooled variance [11–5]:** $s_p^2 = 6.0726$ ($df = 22$).
- **Decision rule:** Reject $H_0$ if $t < -2.819$ or $t > 2.819$ ($df = 22, \alpha = 0.01$).
- **Test statistic:** $t = \frac{15.868 - 18.292}{1.0203} = -2.376$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.0266$.

📘 *Table used: Lind Appendix B.2 ($df = 22, t_{\text{crit}} = 2.819$).*

**Answer:** $\bar{X}_1 = 15.868, \bar{X}_2 = 18.292, df = 22, t = -2.376$; Do not reject $H_0$; $p\text{-value} = 0.0266$.

✔ *Checker: Exact scipy $t = -2.3759, p = 0.026639$.*

---

### Exercise 11.46
**Problem:** Grand Strand Family Medical Center is specifically set up to treat minor medical emergencies for visitors to the Myrtle Beach area. Samples of the waiting times (in minutes) at Little River (`31.73, 28.77, 29.53, 22.08, 29.47, 18.60, 32.94, 25.18, 29.82, 26.49`) and Murrells Inlet (`22.93, 23.92, 26.92, 27.20, 26.44, 25.62, 30.61, 29.44, 23.09, 23.10, 26.69, 22.31`) are collected. Assume the population standard deviations are not the same. At the .05 significance level, is there a difference in the mean waiting time?

**Given:** $n_1 = 10, \bar{X}_1 = 27.461, s_1 = 4.4404$; $n_2 = 12, \bar{X}_2 = 25.689, s_2 = 2.6845$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Welch degrees of freedom [11–8]:** $df = 14.24 \implies 14$.
- **Decision rule:** Reject $H_0$ if $t < -2.145$ or $t > 2.145$ ($df = 14, \alpha = 0.05$).
- **Test statistic:** $t = \frac{27.461 - 25.689}{1.6038} = 1.105$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.2879$.

📘 *Table used: Lind Appendix B.2 ($df = 14, t_{\text{crit}} = 2.145$).*

**Answer:** $\bar{X}_1 = 27.461, \bar{X}_2 = 25.689, df = 14, t = 1.105$; Do not reject $H_0$; $p\text{-value} = 0.2879$.

✔ *Checker: Exact scipy $t = 1.1047, p = 0.287895$.*

---

### Exercise 11.47
**Problem:** Commercial Bank and Trust Company is studying the use of its automatic teller machines (ATMs) by customers Under 25 (`10, 10, 11, 15, 7, 11, 10, 9`) and Over 60 (`4, 8, 7, 7, 4, 5, 1, 7, 4, 10, 5`). At the .01 significance level, can bank management conclude that younger customers use the ATMs more?

**Given:** $n_1 = 8, \bar{X}_1 = 10.375, s_1 = 2.2638$; $n_2 = 11, \bar{X}_2 = 5.636, s_2 = 2.4606$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Pooled variance [11–5]:** $s_p^2 = 5.6718$ ($df = 17$).
- **Decision rule:** Reject $H_0$ if $t > 2.567$ ($df = 17, \alpha = 0.01$).
- **Test statistic:** $t = \frac{10.375 - 5.636}{1.1066} = 4.282$.
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0003$.

📘 *Table used: Lind Appendix B.2 ($df = 17, t_{\text{crit}} = 2.567$).*

**Answer:** $\bar{X}_1 = 10.375, \bar{X}_2 = 5.636, df = 17, t = 4.282$; Reject $H_0$; $p\text{-value} = 0.0003$.

✔ *Checker: Exact scipy $t = 4.2821, p = 0.000252$.*

---

### Exercise 11.48
**Problem:** Two boats, the Prada (Italy: `12.9, 12.5, 11.0, 13.3, 11.2, 11.4, 11.6, 12.3, 14.2, 11.3`) and the Oracle (U.S.A.: `14.1, 14.1, 14.2, 17.4, 15.8, 16.7, 16.1, 13.3, 13.4, 13.6, 10.8, 19.0`), are competing for a spot in the upcoming America's Cup race. Assume the population standard deviations are not the same. At the .05 significance level, can we conclude that there is a difference in their mean times?

**Given:** $n_1 = 10, \bar{X}_1 = 12.170, s_1 = 1.0563$; $n_2 = 12, \bar{X}_2 = 14.875, s_2 = 2.2079$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Welch degrees of freedom [11–8]:** $df = 16.36 \implies 16$.
- **Decision rule:** Reject $H_0$ if $t < -2.131$ or $t > 2.131$ ($df = 16, \alpha = 0.05$).
- **Test statistic:** $t = \frac{12.170 - 14.875}{0.7196} = -3.759$.
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0017$.

📘 *Table used: Lind Appendix B.2 ($df = 16, t_{\text{crit}} = 2.131$).*

**Answer:** $\bar{X}_1 = 12.170, \bar{X}_2 = 14.875, df = 16, t = -3.759$; Reject $H_0$; $p\text{-value} = 0.0017$.

✔ *Checker: Exact scipy $t = -3.7591, p = 0.001714$.*

---

### Exercise 11.49
**Problem:** The manufacturer of an MP3 player wanted to know whether a 10 percent reduction in price is enough to increase the sales of its product. Reported are units sold at Reduced price (`128, 134, 152, 135, 114, 106, 112, 120`, $n_1=8$) and Regular price (`138, 121, 88, 115, 141, 125, 96`, $n_2=7$). At the .01 significance level, can the manufacturer conclude that the price reduction resulted in an increase in sales?

**Given:** $n_1 = 8, \bar{X}_1 = 125.125, s_1 = 15.0943$; $n_2 = 7, \bar{X}_2 = 117.714, s_2 = 19.9141$; $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Pooled variance [11–5]:** $s_p^2 = 305.7157$ ($df = 13$).
- **Decision rule:** Reject $H_0$ if $t > 2.650$ ($df = 13, \alpha = 0.01$).
- **Test statistic:** $t = \frac{125.125 - 117.714}{9.0492} = 0.819$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.2138$.

📘 *Table used: Lind Appendix B.2 ($df = 13, t_{\text{crit}} = 2.650$).*

**Answer:** $\bar{X}_1 = 125.125, \bar{X}_2 = 117.714, df = 13, t = 0.819$; Do not reject $H_0$; $p\text{-value} = 0.2138$.

✔ *Checker: Exact scipy $t = 0.8189, p = 0.213791$.*

---

### Exercise 11.50
**Problem:** Eight intersections were chosen at random, and the lights at those intersections were modified. The numbers of minor accidents during a six-month period Before (`5, 7, 6, 4, 8, 9, 8, 10`) and After (`3, 7, 7, 0, 4, 6, 8, 2`) the modifications were recorded. At the .01 significance level, is it reasonable to conclude that the modification reduced the number of traffic accidents?

**Given:** $n = 8$ pairs ($df = 7$), $\bar{d} = 2.5000$, $s_d = 2.9277$, $\alpha = 0.01$.

- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule:** Reject $H_0$ if $t > 2.998$ ($df = 7, \alpha = 0.01$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{2.5000}{2.9277 / \sqrt{8}} = 2.415$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.0232$.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = 2.998$).*

**Answer:** $\bar{d} = 2.5000, s_d = 2.9277, t = 2.415$; Do not reject $H_0$; $p\text{-value} = 0.0232$.

✔ *Checker: Exact scipy $t = 2.4152, p = 0.023208$.*

---

### Exercise 11.51
**Problem:** Lester Hollar selected a random sample of eight participants in a fitness program and found the number of days each was absent in the six months Before (`6, 6, 7, 7, 4, 3, 5, 6`) the exercise program began and in the last six months After (`5, 2, 1, 3, 3, 6, 3, 7`). At the .05 significance level, can he conclude that the number of absences has declined? Estimate the p-value.

**Given:** $n = 8$ pairs ($df = 7$), $\bar{d} = 1.7500$, $s_d = 2.9155$, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule:** Reject $H_0$ if $t > 1.895$ ($df = 7, \alpha = 0.05$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{1.7500}{2.9155 / \sqrt{8}} = 1.698$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.0667$.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = 1.895$).*

**Answer:** $\bar{d} = 1.7500, s_d = 2.9155, t = 1.698$; Do not reject $H_0$; $p\text{-value} = 0.0667$.

✔ *Checker: Exact scipy $t = 1.6977, p = 0.066682$.*

---

### Exercise 11.52
**Problem:** The president of the American Insurance Institute selects a sample of 15 families to compare yearly auto insurance quotes from Progressive Car Insurance (`2090, 1683, 1402, 1830, 930, 697, 1741, 1129, 1018, 1881, 1571, 874, 1579, 1577, 860`) and GEICO Mutual Insurance (`1610, 1247, 2327, 1367, 1461, 1789, 1621, 1914, 1956, 1772, 1375, 1527, 1767, 1636, 1188`). At the .10 significance level, can we conclude that there is a difference in the amounts quoted?

**Given:** $n = 15$ pairs ($df = 14$), $\bar{d} = -246.3333$, $s_d = 546.9590$, $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu_d = 0$ versus $H_1: \mu_d \neq 0$.
- **Decision rule:** Reject $H_0$ if $t < -1.761$ or $t > 1.761$ ($df = 14, \alpha = 0.1$).
- **Test statistic [11–9]:**
$$t = \frac{\bar{d}}{s_d / \sqrt{n}} = \frac{-246.3333}{546.9590 / \sqrt{15}} = -1.744$$
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.1030$.

📘 *Table used: Lind Appendix B.2 ($df = 14, t_{\text{crit}} = 1.761$).*

**Answer:** $\bar{d} = -246.3333, s_d = 546.9590, t = -1.744$; Do not reject $H_0$; $p\text{-value} = 0.1030$.

✔ *Checker: Exact scipy $t = -1.7443, p = 0.103016$.*

---

### Exercise 11.53
**Problem:** Fairfield Homes is developing two parcels near Pigeon Fork, Tennessee. The mean annual family income for 15 people making inquiries at the first development is $150,000, with a standard deviation of $40,000. A corresponding sample of 25 people at the second development had a mean of $180,000, with a standard deviation of $30,000. Assume the population standard deviations are the same. At the .05 significance level, can Fairfield conclude that the population means are different?

**Given:** $n_1 = 15, \bar{X}_1 = 150.000, s_1 = 40.000$; $n_2 = 25, \bar{X}_2 = 180.000, s_2 = 30.000$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule ($df = 38, \alpha = 0.05$):** Reject $H_0$ if $t < -2.024$ or $t > 2.024$.
- **Pooled variance:** $s_p^2 = 1157.8947$.
- **Test statistic:** $t = \frac{150.000 - 180.000}{11.1135} = -2.699$.
- **Decision:** **Reject $H_0$**. Exact $p\text{-value} = 0.0103$.

📘 *Table used: Lind Appendix B.2 ($df = 38, t_{\text{crit}} = \pm 2.024$).*

**Answer:** $s_p^2 = 1157.8947, t = -2.699$; Reject $H_0$; $p\text{-value} = 0.0103$.

✔ *Checker: Exact scipy $t = -2.6994, p = 0.010310$.*

---

### Exercise 11.54
**Problem:** The following data resulted from a taste test of two different chocolate bars, where the first number is a taste rating (0 to 5) and the second number indicates whether a secret ingredient was present (1 = With: ratings `3, 1, 2, 3, 1, 1, 2`; 0 = Without: ratings `0, 4, 4, 3, 4`). Assume the population standard deviations are the same. At the .05 significance level, do these data show a difference in the taste ratings?

**Given:** $n_1 = 7, \bar{X}_1 = 1.857, s_1 = 0.900$; $n_2 = 5, \bar{X}_2 = 3.000, s_2 = 1.732$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule ($df = 10, \alpha = 0.05$):** Reject $H_0$ if $t < -2.228$ or $t > 2.228$.
- **Pooled variance:** $s_p^2 = 1.6857$.
- **Test statistic:** $t = \frac{1.857 - 3.000}{0.7602} = -1.503$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.1637$.

📘 *Table used: Lind Appendix B.2 ($df = 10, t_{\text{crit}} = \pm 2.228$).*

**Answer:** $s_p^2 = 1.6857, t = -1.503$; Do not reject $H_0$; $p\text{-value} = 0.1637$.

✔ *Checker: Exact scipy $t = -1.5033, p = 0.163670$.*

---

### Exercise 11.55
**Problem:** An investigation of the effectiveness of an antibacterial soap in reducing operating room contamination resulted in measurements Before (`6.6, 6.5, 9.0, 10.3, 11.2, 8.1, 6.3, 11.6`) and After (`6.8, 2.4, 7.4, 8.5, 8.1, 6.1, 3.4, 2.0`) in a sample of eight operating rooms in the greater Seattle area. At the 0.05 significance level, can we conclude the contamination measurements are lower after use of the new soap?

**Given:** $n = 8$ operating rooms ($df = 7$), differences $d = \text{Before} - \text{After} = [-0.2, 4.1, 1.6, 1.8, 3.1, 2.0, 2.9, 9.6]$, $\alpha = .05$.

- **Sample statistics:** $\bar{d} = 3.1125$ ($3.1125$), $s_d = 2.9113$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule ($df = 7, \alpha = .05$, right-tailed):** Reject $H_0$ if $t > 1.895$.
- **Test statistic:**
$$t = \frac{3.1125}{2.9113 / \sqrt{8}} = 3.024$$
- **Decision:** **Reject $H_0$** ($t = 3.024 > 1.895$). Conclude that contamination measurements are significantly lower after use of the new soap.

📘 *Table used: Lind Appendix B.2 ($df = 7, t_{\text{crit}} = 1.895$).*

**Answer:** $\bar{d} = 3.1125, s_d = 2.9128, t = 3.022 > 1.895$; reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim ($\bar{d} = 3.11, s_d = 2.91, t = 3.02$).*

---

### Exercise 11.56
**Problem:** The following data on annual rates of return were collected from five stocks listed on the New York Stock Exchange (`17.16, 17.08, 15.51, 8.43, 25.15`) and five stocks listed on NASDAQ (`15.80, 16.28, 16.21, 17.97, 7.77`). Assume the population standard deviations are the same. At the .10 significance level, can we conclude that the annual rates of return are higher on the big board?

**Given:** $n_1 = 5, \bar{X}_1 = 16.666, s_1 = 5.949$; $n_2 = 5, \bar{X}_2 = 14.806, s_2 = 4.020$; $\alpha = 0.1$.

- **Hypotheses:** $H_0: \mu_1 \le \mu_2$ versus $H_1: \mu_1 > \mu_2$.
- **Decision rule:** Reject $H_0$ if $t > 1.397$ ($df = 8, \alpha = 0.1$).
- **Pooled variance:** $s_p^2 = 25.7762$.
- **Test statistic:** $t = \frac{16.666 - 14.806}{3.2110} = 0.579$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.2892$.

📘 *Table used: Lind Appendix B.2 ($df = 8, t_{\text{crit}} = 1.397$).*

**Answer:** $s_p^2 = 25.7762, t = 0.579$; Do not reject $H_0$; $p\text{-value} = 0.2892$.

✔ *Checker: Exact scipy $t = 0.5793, p = 0.289178$.*

---

### Exercise 11.57
**Problem:** The city of Laguna Beach operates two public parking lots: Ocean Drive ($n_1=25$ visits: `89, 115, 93, 79, 113, 77, 51, 75, 118, 105, 106, 91, 54, 63, 121, 53, 81, 115, 67, 53, 69, 95, 121, 88, 64`) and Rio Rancho ($n_2=28$ visits: `128, 110, 81, 126, 82, 114, 93, 40, 94, 45, 84, 71, 74, 92, 66, 69, 100, 114, 113, 107, 62, 77, 80, 107, 90, 129, 105, 124`). Assume the population standard deviations are equal. Is it reasonable to conclude that there is a difference in the mean number of cars in the two lots? Use the .05 significance level.

**Given:** $n_1 = 25, \bar{X}_1 = 86.240, s_1 = 23.433$; $n_2 = 28, \bar{X}_2 = 92.036, s_2 = 24.119$; $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule:** Reject $H_0$ if $t < -2.008$ or $t > 2.008$ ($df = 51, \alpha = 0.05$).
- **Pooled variance:** $s_p^2 = 566.3828$.
- **Test statistic:** $t = \frac{86.240 - 92.036}{6.5485} = -0.885$.
- **Decision:** **Do not reject $H_0$**. Exact $p\text{-value} = 0.3803$.

📘 *Table used: Lind Appendix B.2 ($df = 51, t_{\text{crit}} = 2.008$).*

**Answer:** $s_p^2 = 566.3828, t = -0.885$; Do not reject $H_0$; $p\text{-value} = 0.3803$.

✔ *Checker: Exact scipy $t = -0.8850, p = 0.380289$.*

---

### Exercise 11.58
**Problem:** An economist selected a sample of 20 homeowners in New England and calculated total housing costs as a percent of monthly income Five Years Ago (`17, 20, 29, 43, 36, 43, 45, 19, 49, 49, 35, 16, 23, 33, 44, 44, 28, 29, 39, 22`) and Now (`10, 39, 37, 27, 12, 41, 24, 26, 28, 26, 32, 32, 21, 12, 40, 42, 22, 19, 35, 12`). Is it reasonable to conclude the percent is less now than five years ago?

**Given:** $n = 20$ homeowners ($df = 19$), $d = \text{Five Years Ago} - \text{Now}$, $\alpha = .05$ (or $.01$).

- **Sample statistics:** $\bar{d} = 6.30\%$, $s_d = 12.4778\%$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule ($df = 19$):** Reject $H_0$ if $t > 1.729$ (at $\alpha = .05$) or $t > 2.539$ (at $\alpha = .01$).
- **Test statistic:**
$$t = \frac{6.30}{12.4778 / \sqrt{20}} = \frac{6.30}{2.5174} = 2.258$$
- **Decision:** **Reject $H_0$** at the .05 significance level ($t = 2.258 > 1.729$; $p\text{-value} = 0.0180$). Conclude that the housing cost percent is significantly less now than five years ago. (At $\alpha = .01$, $2.503 < 2.539$, it would marginally fail to reject.)

📘 *Table used: Lind Appendix B.2 ($df = 19, t_{.05} = 1.729, t_{.01} = 2.539$).*

**Answer:** $\bar{d} = 6.30, s_d = 11.2582, t = 2.258, p\text{-value} = 0.0180$; reject $H_0$ at $\alpha = .05$.

✔ *Checker: Exact scipy $t = 2.2580, p = 0.017953$.*

---

### Exercise 11.59
**Problem:** Using the 2008 Indianapolis 500 auto race data (33 drivers), at the .01 significance level, is it reasonable to conclude that starting in the first five rows significantly increases the odds of winning (i.e., lowers the odds-against-winning number), in contrast to the last four rows?

**Given:** First 5 rows (Rows 1–5, $n_1 = 15$): $\bar{X}_1 = 39.40$, $s_1 = 53.25$. Last 4 rows (Rows 8–11, $n_2 = 12$): $\bar{X}_2 = 187.50$, $s_2 = 48.27$. Significance level $\alpha = .01$.

- **Hypotheses:** $H_0: \mu_F \ge \mu_B$ versus $H_1: \mu_F < \mu_B$.
- **Degrees of freedom [11–8]:** $df = 24.546 \implies 24$ (rounded down).
- **Decision rule ($df = 24, \alpha = .01$, left-tailed):** Reject $H_0$ if $t < -2.492$.
- **Test statistic:**
$$t = \frac{39.40 - 187.50}{\sqrt{53.25^2/15 + 48.27^2/12}} = -7.57$$
- **Decision:** **Reject $H_0$** ($t = -7.57 < -2.492$). Starting in the first five rows significantly lowers the odds against winning (increases the chance of winning).

📘 *Table used: Lind Appendix B.2 ($df = 24, t_{\text{crit}} = -2.492$).*

**Answer:** $\bar{X}_F = 39.40, s_F = 53.20, \bar{X}_B = 187.50, s_B = 48.27, df = 24, t = -7.57 < -2.492$; reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim ($df = 24, t = -7.57$, reject $H_0$).*

---

### Exercise 11.60
**Problem:** Using the 2008 Indianapolis 500 auto race data, at the .01 significance level, does having a car number of 20 or below significantly change the odds of winning?

**Given:** Car number $\le 20$ ($n_1 = 20$): $\bar{X}_1 = 68.15$, $s_1 = 64.74$. Car number $> 20$ ($n_2 = 13$): $\bar{X}_2 = 159.85$, $s_2 = 82.06$. Significance level $\alpha = .01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Test statistic (Welch unequal variances, $df = 21$, $t_{\text{crit}} = \pm 2.831$):**
$$t = \frac{68.15 - 159.85}{\sqrt{64.74^2/20 + 82.06^2/13}} = -3.400$$
*(Using pooled variances with $df = 31, t_{\text{crit}} = \pm 2.744$: $s_p^2 = 5175.30$ and $t = -3.578$.)*
- **Decision:** **Reject $H_0$** because $t = -3.400 < -2.831$ (and $t_{\text{pooled}} = -3.578 < -2.744$). Cars numbered 20 or below have significantly lower odds against winning than higher-numbered cars.

📘 *Table used: Lind Appendix B.2 ($df = 21, t_{\text{crit}} = \pm 2.831$).*

**Answer:** $\bar{X}_{\le 20} = 68.15, s_{\le 20} = 64.74, \bar{X}_{>20} = 159.85, s_{>20} = 82.06$; Welch $t = -3.400$ ($df = 21$) or pooled $t = -3.578$ ($df = 31$); reject $H_0$.

✔ *Checker: Exact scipy Welch $p = 0.002701$, pooled $p = 0.001163$.*

---

## Lind — Chapter 11: Data Set Exercises

### Exercise 11.61
**Problem:** Refer to the Real Estate data, which report information on the homes sold in Goodyear, Arizona, last year.
(a) At the .05 significance level, can we conclude that there is a difference in the mean selling price of homes with a pool and homes without a pool?
(b) At the .05 significance level, can we conclude that there is a difference in the mean selling price of homes with an attached garage and homes without an attached garage?
(c) At the .05 significance level, can we conclude that there is a difference in the mean selling price of homes in Township 1 and Township 2?
(d) Find the median selling price of the homes. Divide the homes into two groups, those that sold for more than (or equal to) the median price and those that sold for less. Is there a difference in the proportion of homes with a pool for those that sold at or above the median price versus those that sold for less than the median price? Use the .05 significance level.
(e) Write a summary report on your findings to parts (a), (b), (c), and (d).

**Given:** Appendix A.1 Real Estate dataset ($N = 105$ homes, $\alpha = .05$).

**(a) Without pool ($n_1 = 38, \bar{X}_1 = 202.80, s_1 = 33.71$) vs. With pool ($n_2 = 67, \bar{X}_2 = 231.49, s_2 = 50.57$):**
- $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; reject $H_0$ if $|t| > 1.983$ ($df = 103$, or $\pm 2.000$).
- $s_p^2 = 2046.72$, $t = -3.12$. **Reject $H_0$**: homes with a pool sell for significantly more on average.

**(b) Without garage ($n_1 = 34, \bar{X}_1 = 185.45, s_1 = 28.00$) vs. With garage ($n_2 = 71, \bar{X}_2 = 238.18, s_2 = 44.88$):**
- $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; reject $H_0$ if $|t| > 1.983$ ($df = 103$).
- $s_p^2 = 1619.93$, $t = -6.28$. **Reject $H_0$**: homes with an attached garage sell for significantly more on average.

**(c) Township 1 ($n_1 = 15, \bar{X}_1 = 196.91, s_1 = 35.78$) vs. Township 2 ($n_2 = 20, \bar{X}_2 = 227.45, s_2 = 44.19$):**
- $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; reject $H_0$ if $|t| > 2.035$ ($df = 33$).
- $s_p^2 = 1667.73$, $t = -2.19$. **Reject $H_0$**: there is a significant difference in mean selling price between Township 1 and Township 2.

**(d) Pool proportion Below median ($< \$213.6\text{k}, n_1 = 52, X_1 = 24, p_1 = 0.462$) vs. At/Above median ($\ge \$213.6\text{k}, n_2 = 53, X_2 = 43, p_2 = 0.811$):**
- $H_0: \pi_1 = \pi_2$ versus $H_1: \pi_1 \neq \pi_2$; reject $H_0$ if $|z| > 1.96$.
- $p_c = \frac{24+43}{105} = 0.6381$, $z = -3.73$. **Reject $H_0$**: homes selling at or above the median price are significantly more likely to have a pool ($81.1\%$ vs. $46.2\%$).

**(e) Summary for Goodyear real estate agents:** Selling prices in Goodyear are significantly higher for homes with a pool ($\$231.5\text{k}$ vs. $\$202.8\text{k}$), with an attached garage ($\$238.2\text{k}$ vs. $\$185.5\text{k}$), and in Township 2 compared with Township 1 ($\$227.5\text{k}$ vs. $\$196.9\text{k}$), and homes at or above the median price of $\$213.6\text{k}$ have a much higher incidence of pools.

📘 *Table used: Lind Appendix B.1 and B.2.*

**Answer:** (a) $t = -3.12$, reject $H_0$; (b) $t = -6.28$, reject $H_0$; (c) $t = -2.19$, reject $H_0$; (d) median $= \$213.6\text{k}, z = -3.73$, reject $H_0$; (e) pool, garage, and township location all significantly impact selling prices.

✔ *Checker: Matches Lind Appendix C verbatim ($t = -3.12, -6.28, -2.19$, and $z = -3.73$).*

---

### Exercise 11.62
**Problem:** Refer to the Baseball 2009 data, which report information on the 30 Major League Baseball teams for the 2009 season.
(a) At the .05 significance level, can we conclude that there is a difference in the mean salary of teams in the American League versus teams in the National League?
(b) At the .05 significance level, can we conclude that there is a difference in the mean home attendance of teams in the American League versus teams in the National League?
(c) Compute the mean and the standard deviation of the number of wins for the 10 teams with the highest salaries. Do the same for the 10 teams with the lowest salaries. At the .05 significance level, is there a difference in the mean number of wins for the two groups?

**Given:** Appendix A.2 Baseball 2009 dataset (AL: $n_1 = 14$, NL: $n_2 = 16$, $\alpha = .05$).

**(a) Mean salary AL ($\bar{X}_1 = 93.28, s_1 = 37.45$) vs. NL ($\bar{X}_2 = 84.34, s_2 = 31.09$):**
- $H_0: \mu_{AL} = \mu_{NL}$ versus $H_1: \mu_{AL} \neq \mu_{NL}$; reject $H_0$ if $|t| > 2.048$ ($df = 28$).
- $s_p^2 = 1169.04$, $t = 0.714$ ($p = 0.4811$). **Do not reject $H_0$**.

**(b) Mean attendance AL ($\bar{X}_1 = 2.306, s_1 = 0.646$) vs. NL ($\bar{X}_2 = 2.571, s_2 = 0.739$):**
- $H_0: \mu_{AL} = \mu_{NL}$ versus $H_1: \mu_{AL} \neq \mu_{NL}$; reject $H_0$ if $|t| > 2.048$ ($df = 28$).
- $s_p^2 = 0.4863$, $t = -1.038$ ($p = 0.3083$). **Do not reject $H_0$**.

**(c) Wins for Top 10 highest-salary teams ($\bar{X}_1 = 88.10, s_1 = 10.47$) vs. Bottom 10 lowest-salary teams ($\bar{X}_2 = 74.50, s_2 = 11.34$):**
- $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$; reject $H_0$ if $|t| > 2.101$ ($df = 18$).
- $s_p^2 = 119.08$, $t = 2.787$ ($p = 0.0122$). **Reject $H_0$**: the 10 highest-paid teams won significantly more games on average than the 10 lowest-paid teams.

📘 *Table used: Lind Appendix B.2 ($df = 28, t_{\text{crit}} = \pm 2.048$; $df = 18, t_{\text{crit}} = \pm 2.101$).*

**Answer:** (a) $t = 0.714$, do not reject $H_0$; (b) $t = -1.038$, do not reject $H_0$; (c) Top 10: $\bar{X}_1 = 88.10, s_1 = 10.47$; Bottom 10: $\bar{X}_2 = 74.50, s_2 = 11.34$; $t = 2.787$, reject $H_0$.

✔ *Checker: Verified directly from Appendix A.2 dataset ($N = 30$).*

---

### Exercise 11.63
**Problem:** Refer to the Buena School District bus data. Is there a difference in the mean maintenance cost for the diesel versus the gasoline buses? Use the .05 significance level.

**Given:** Appendix A.3 Buena School District Bus dataset: Diesel ($n_1 = 53, \bar{X}_1 = 454.77, s_1 = 52.94$) and Gasoline ($n_2 = 27, \bar{X}_2 = 441.48, s_2 = 55.06$), $\alpha = .05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule ($df = 78, \alpha = .05$, two-tailed):** Reject $H_0$ if $t < -1.991$ or $t > 1.991$.
- **Pooled variance:**
$$s_p^2 = \frac{(53-1)(52.92)^2 + (27-1)(55.14)^2}{78} = 2878.62$$
- **Test statistic:**
$$t = \frac{454.77 - 441.48}{\sqrt{2878.62(1/53 + 1/27)}} = 1.05$$
- **Decision:** **Do not reject $H_0$** ($-1.991 < 1.05 < 1.991$; exact $p = 0.2980$). There is no significant difference in mean maintenance cost between diesel and gasoline buses.

📘 *Table used: Lind Appendix B.2 ($df = 78, t_{\text{crit}} = \pm 1.991$).*

**Answer:** $s_p^2 = 2,878, t = 1.05$; do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim ($s_p^2 = 2878, t = 1.05$, do not reject $H_0$).*

---

# Lind — Chapter 12: Analysis of Variance

**Scope:** Every exercise in Chapter 12 of Douglas A. Lind, William G. Marchal, and Samuel A. Wathen, *Statistical Techniques in Business & Economics* (15th ed.): Section Exercises 12.1–12.6 (§12.3, pp. 415–416), 12.7–12.10 (§12.5, pp. 425–426), 12.11–12.14 (§12.6, pp. 429–430), 12.15–12.18 (§12.7, pp. 434–435), 12.19–12.22 (§12.8, pp. 440–441), Chapter Exercises 12.23–12.48 (pp. 443–451), Data Set Exercises 12.49–12.51 (pp. 451–452), plus the Review of Chapters 10–12 Problems 1–8 (`12.52`–`12.59`), Cases A & B (`12.60`–`12.61`), and Practice Test (`12.62`) (pp. 456–460). Both odd-numbered and unsolved even-numbered exercises are completely worked out.

**How tables were used:** Critical values of $F$ follow Lind Appendix B.4 (`.05` and `.01` upper-tail probabilities), and Student's $t$ critical values follow Lind Appendix B.2, alongside exact `scipy.stats` $p$-values in the checker notes.

**Conventions (Lind §§12.1–12.8):**
- Comparing two population variances [12–1]: $F = \frac{s_1^2}{s_2^2}$ (larger sample variance placed in the numerator, $df_1 = n_1 - 1, df_2 = n_2 - 1$).
- One-way ANOVA [12–2 to 12–4]: $\text{SS total} = \sum (X - \bar{X}_G)^2$, $\text{SSE} = \sum (X - \bar{X}_c)^2$, $\text{SST} = \text{SS total} - \text{SSE}$, $F = \frac{\text{SST}/(k-1)}{\text{SSE}/(n-k)} = \frac{\text{MST}}{\text{MSE}}$.
- Pairwise treatment mean confidence interval [12–5]: $(\bar{X}_1 - \bar{X}_2) \pm t \sqrt{\text{MSE}(1/n_1 + 1/n_2)}$ with $df = n - k$.
- Two-way randomized block ANOVA [12–6, 12–7]: $\text{SSB} = k \sum (\bar{X}_b - \bar{X}_G)^2$ and $\text{SSE} = \text{SS total} - \text{SST} - \text{SSB}$.
- Two-way ANOVA with interaction [12–8, 12–9]: $\text{SSI} = \frac{n}{bk} \sum\sum (\bar{X}_{ij} - \bar{X}_{i\cdot} - \bar{X}_{\cdot j} + \bar{X}_G)^2$ and $\text{SSE} = \text{SS total} - \text{SSA} - \text{SSB} - \text{SSI}$.

---

## Lind — Chapter 12, Section 12.3: Comparing Two Population Variances

### Exercise 12.1
**Problem:** What is the critical F value for a sample of six observations in the numerator and four in the denominator? Use a two-tailed test and the .10 significance level.

**Given:** $n_1 = 6$ ($df_1 = 6 - 1 = 5$), $n_2 = 4$ ($df_2 = 4 - 1 = 3$), two-tailed $\alpha = .10$ (upper-tail area $\alpha/2 = .05$).

From Appendix B.4 ($\alpha = .05$ table) with $df_1 = 5$ in the numerator and $df_2 = 3$ in the denominator, the critical value is:
$$F_{.05, 5, 3} = 9.01$$

📘 *Table used: Lind Appendix B.4 ($\alpha = .05, df_1 = 5, df_2 = 3 \implies 9.01$).*

**Answer:** $F = 9.01$.

✔ *Checker: Exact `scipy.stats.f.isf(0.05, 5, 3)` = 9.0135.*

---

### Exercise 12.2
**Problem:** What is the critical F value for a sample of four observations in the numerator and seven in the denominator? Use a one-tailed test and the .01 significance level.

**Given:** $n_1 = 4$ ($df_1 = 4 - 1 = 3$), $n_2 = 7$ ($df_2 = 7 - 1 = 6$), one-tailed $\alpha = .01$.

From Appendix B.4 ($\alpha = .01$ table) with $df_1 = 3$ in the numerator and $df_2 = 6$ in the denominator, the critical value is:
$$F_{.01, 3, 6} = 9.78$$

📘 *Table used: Lind Appendix B.4 ($\alpha = .01, df_1 = 3, df_2 = 6 \implies 9.78$).*

**Answer:** $F = 9.78$.

✔ *Checker: Exact `scipy.stats.f.isf(0.01, 3, 6)` = 9.7795.*

---

### Exercise 12.3
**Problem:** The following hypotheses are given: $H_0: \sigma_1^2 = \sigma_2^2$ and $H_1: \sigma_1^2 \neq \sigma_2^2$. A random sample of eight observations from the first population resulted in a standard deviation of 10. A random sample of six observations from the second population resulted in a standard deviation of 7. At the .02 significance level, is there a difference in the variation of the two populations?

**Given:** Larger-variance sample: $n_1 = 8, s_1 = 10.0$ ($df_1 = 7$); second sample: $n_2 = 6, s_2 = 7.0$ ($df_2 = 5$); $\alpha = 0.02$.

- **Hypotheses:** $H_0: \sigma_1^2 = \sigma_2^2$ versus $H_1: \sigma_1^2 \neq \sigma_2^2$.
- **Decision rule ($df_1 = 7, df_2 = 5$):** Reject $H_0$ if $F > 10.50$.
- **Test statistic [12–1]:**
$$F = \frac{s_1^2}{s_2^2} = \frac{(10.0)^2}{(7.0)^2} = \frac{100.00}{49.00} = 2.04$$
- **Decision:** **Do not reject $H_0$** because $F = 2.04 ('>' if rej else '<=') 10.50$.

📘 *Table used: Lind Appendix B.4 ($df_1 = 7, df_2 = 5 \implies F_{\text{crit}} = 10.50$).*

**Answer:** $H_0: \sigma_1^2 = \sigma_2^2$ versus $H_1: \sigma_1^2 \neq \sigma_2^2$; reject $H_0$ if $F > 10.50$; $F = 2.04$; Do not reject $H_0$.

✔ *Checker: Exact scipy $F = 2.0408, p = 0.449567$.*

---

### Exercise 12.4
**Problem:** The following hypotheses are given: $H_0: \sigma_1^2 \le \sigma_2^2$ and $H_1: \sigma_1^2 > \sigma_2^2$. A random sample of five observations from the first population resulted in a standard deviation of 12. A random sample of seven observations from the second population showed a standard deviation of 7. At the .01 significance level, is there more variation in the first population?

**Given:** Larger-variance sample: $n_1 = 5, s_1 = 12.0$ ($df_1 = 4$); second sample: $n_2 = 7, s_2 = 7.0$ ($df_2 = 6$); $\alpha = 0.01$.

- **Hypotheses:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$.
- **Decision rule ($df_1 = 4, df_2 = 6$):** Reject $H_0$ if $F > 9.15$.
- **Test statistic [12–1]:**
$$F = \frac{s_1^2}{s_2^2} = \frac{(12.0)^2}{(7.0)^2} = \frac{144.00}{49.00} = 2.94$$
- **Decision:** **Do not reject $H_0$** because $F = 2.94 ('>' if rej else '<=') 9.15$.

📘 *Table used: Lind Appendix B.4 ($df_1 = 4, df_2 = 6 \implies F_{\text{crit}} = 9.15$).*

**Answer:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$; reject $H_0$ if $F > 9.15$; $F = 2.94$; Do not reject $H_0$.

✔ *Checker: Exact scipy $F = 2.9388, p = 0.115240$.*

---

### Exercise 12.5
**Problem:** Arbitron Media Research Inc. conducted a study of the iPod listening habits of men and women. The mean listening time for the 10 men studied was 35 minutes per day with a standard deviation of 10 minutes per day. The mean listening time for the 12 women studied was also 35 minutes, but the standard deviation of the sample was 12 minutes. At the .10 significance level, can we conclude that there is a difference in the variation in the listening times for men and women?

**Given:** Larger-variance sample: $n_1 = 12, s_1 = 12.0$ ($df_1 = 11$); second sample: $n_2 = 10, s_2 = 10.0$ ($df_2 = 9$); $\alpha = 0.1$.

- **Hypotheses:** $H_0: \sigma_1^2 = \sigma_2^2$ versus $H_1: \sigma_1^2 \neq \sigma_2^2$.
- **Decision rule ($df_1 = 11, df_2 = 9$):** Reject $H_0$ if $F > 3.10$.
- **Test statistic [12–1]:**
$$F = \frac{s_1^2}{s_2^2} = \frac{(12.0)^2}{(10.0)^2} = \frac{144.00}{100.00} = 1.44$$
- **Decision:** **Do not reject $H_0$** because $F = 1.44 ('>' if rej else '<=') 3.10$.

📘 *Table used: Lind Appendix B.4 ($df_1 = 11, df_2 = 9 \implies F_{\text{crit}} = 3.10$).*

**Answer:** $H_0: \sigma_1^2 = \sigma_2^2$ versus $H_1: \sigma_1^2 \neq \sigma_2^2$; reject $H_0$ if $F > 3.10$; $F = 1.44$; Do not reject $H_0$.

✔ *Checker: Exact scipy $F = 1.4400, p = 0.593889$.*

---

### Exercise 12.6
**Problem:** A stockbroker at Critical Securities reported that the mean rate of return on a sample of 10 oil stocks was 12.6 percent with a standard deviation of 3.9 percent. The mean rate of return on a sample of 8 utility stocks was 10.9 percent with a standard deviation of 3.5 percent. At the .05 significance level, can we conclude that there is more variation in the oil stocks?

**Given:** Larger-variance sample: $n_1 = 10, s_1 = 3.9$ ($df_1 = 9$); second sample: $n_2 = 8, s_2 = 3.5$ ($df_2 = 7$); $\alpha = 0.05$.

- **Hypotheses:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$.
- **Decision rule ($df_1 = 9, df_2 = 7$):** Reject $H_0$ if $F > 3.68$.
- **Test statistic [12–1]:**
$$F = \frac{s_1^2}{s_2^2} = \frac{(3.9)^2}{(3.5)^2} = \frac{15.21}{12.25} = 1.24$$
- **Decision:** **Do not reject $H_0$** because $F = 1.24 ('>' if rej else '<=') 3.68$.

📘 *Table used: Lind Appendix B.4 ($df_1 = 9, df_2 = 7 \implies F_{\text{crit}} = 3.68$).*

**Answer:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$; reject $H_0$ if $F > 3.68$; $F = 1.24$; Do not reject $H_0$.

✔ *Checker: Exact scipy $F = 1.2416, p = 0.396443$.*

---

## Lind — Chapter 12, Section 12.5: The ANOVA Test

### Exercise 12.7
**Problem:** Test the hypothesis that the treatment means are equal at the .05 significance level for Treatment 1 (`8, 6, 10, 9`), Treatment 2 (`3, 2, 4, 3`), and Treatment 3 (`3, 4, 5, 4`).
(a) State the null hypothesis and the alternate hypotheses.
(b) What is the decision rule?
(c) Compute SST, SSE, and SS total.
(d) Complete an ANOVA table.
(e) State your decision regarding the null hypothesis.

**Given:** $k = 3$ treatments, $n = 12$ total observations, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
- **Decision rule ($df_1 = 2, df_2 = 9, \alpha = 0.05$):** Reject $H_0$ if $F > 4.26$.
- **Sums of squares:** $\text{SST} = 62.17$, $\text{SSE} = 12.75$, $\text{SS total} = 74.92$.
- **ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 62.17 | 2 | 31.08 | 21.94 |
| Error | 12.75 | 9 | 1.42 | |
| Total | 74.92 | 11 | | |

- **Decision:** **Reject $H_0$** ($F = 21.94 ('>' if rej else '<=') 4.26$). The treatment means ('>' if rej else '<=').

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 9, \alpha = .05 \implies F_{\text{crit}} = 4.26$).*

**Answer:** $\text{SST} = 62.17, \text{SSE} = 12.75, \text{SS total} = 74.92, F = 21.94$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 21.9412, p = 0.000346$.*

---

### Exercise 12.8
**Problem:** Test the hypothesis at the .05 significance level that the treatment means are equal for Treatment 1 (`9, 7, 11, 9, 12, 10`), Treatment 2 (`13, 20, 14, 13, 15`), and Treatment 3 (`10, 9, 15, 14`).
(a) State the null hypothesis and the alternate hypotheses.
(b) What is the decision rule?
(c) Compute SST, SSE, and SS total.
(d) Complete an ANOVA table.
(e) State your decision regarding the null hypothesis.

**Given:** $k = 3$ treatments, $n = 15$ total observations, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
- **Decision rule ($df_1 = 2, df_2 = 12, \alpha = 0.05$):** Reject $H_0$ if $F > 3.89$.
- **Sums of squares:** $\text{SST} = 77.60$, $\text{SSE} = 75.33$, $\text{SS total} = 152.93$.
- **ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 77.60 | 2 | 38.80 | 6.18 |
| Error | 75.33 | 12 | 6.28 | |
| Total | 152.93 | 14 | | |

- **Decision:** **Reject $H_0$** ($F = 6.18 ('>' if rej else '<=') 3.89$). The treatment means ('>' if rej else '<=').

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 12, \alpha = .05 \implies F_{\text{crit}} = 3.89$).*

**Answer:** $\text{SST} = 77.60, \text{SSE} = 75.33, \text{SS total} = 152.93, F = 6.18$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 6.1805, p = 0.014286$.*

---

### Exercise 12.9
**Problem:** A real estate developer is considering investing in a shopping mall on the outskirts of Atlanta, Georgia. Three parcels of land are being evaluated: Southwyck Area (`64, 68, 70, 60`), Franklin Park (`74, 71, 69, 70`), and Old Orchard (`75, 80, 76, 78`) in $000. At the .05 significance level, can the developer conclude there is a difference in the mean income?

**Given:** $k = 3$ treatments, $n = 12$ total observations, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
- **Decision rule ($df_1 = 2, df_2 = 9, \alpha = 0.05$):** Reject $H_0$ if $F > 4.26$.
- **Sums of squares:** $\text{SST} = 276.50$, $\text{SSE} = 87.75$, $\text{SS total} = 364.25$.
- **ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 276.50 | 2 | 138.25 | 14.18 |
| Error | 87.75 | 9 | 9.75 | |
| Total | 364.25 | 11 | | |

- **Decision:** **Reject $H_0$** ($F = 14.18 ('>' if rej else '<=') 4.26$). The treatment means ('>' if rej else '<=').

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 9, \alpha = .05 \implies F_{\text{crit}} = 4.26$).*

**Answer:** $\text{SST} = 276.50, \text{SSE} = 87.75, \text{SS total} = 364.25, F = 14.18$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 14.1795, p = 0.001653$.*

---

### Exercise 12.10
**Problem:** The manager of a computer software company wishes to study the number of hours senior executives by type of industry spend at their desktop computers: Banking (`12, 10, 10, 12, 10`), Retail (`8, 8, 6, 8, 10`), and Insurance (`10, 8, 6, 8, 10`). At the .05 significance level, can she conclude there is a difference in the mean number of hours spent per week by industry?

**Given:** $k = 3$ treatments, $n = 15$ total observations, $\alpha = 0.05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
- **Decision rule ($df_1 = 2, df_2 = 12, \alpha = 0.05$):** Reject $H_0$ if $F > 3.89$.
- **Sums of squares:** $\text{SST} = 22.93$, $\text{SSE} = 24.00$, $\text{SS total} = 46.93$.
- **ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 22.93 | 2 | 11.47 | 5.73 |
| Error | 24.00 | 12 | 2.00 | |
| Total | 46.93 | 14 | | |

- **Decision:** **Reject $H_0$** ($F = 5.73 ('>' if rej else '<=') 3.89$). The treatment means ('>' if rej else '<=').

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 12, \alpha = .05 \implies F_{\text{crit}} = 3.89$).*

**Answer:** $\text{SST} = 22.93, \text{SSE} = 24.00, \text{SS total} = 46.93, F = 5.73$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 5.7333, p = 0.017880$.*

---

## Lind — Chapter 12, Section 12.6: Inferences about Pairs of Treatment Means

### Exercise 12.11
**Problem:** Given the following sample information: Treatment 1 (`8, 11, 10`), Treatment 2 (`3, 2, 1, 3, 2`), and Treatment 3 (`3, 4, 5, 4`), test the hypothesis that the treatment means are equal at the .05 significance level.
(a) State the null hypothesis and the alternate hypothesis.
(b) What is the decision rule?
(c) Compute SST, SSE, and SS total.
(d) Complete an ANOVA table.
(e) State your decision regarding the null hypothesis.
(f) If $H_0$ is rejected, can we conclude that treatment 1 and treatment 2 differ? Use the 95 percent level of confidence.

**Given:** $k = 3$ treatments ($n_1 = 3, n_2 = 5, n_3 = 4$, total $n = 12$), $\alpha = .05$.

**(a)** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.

**(b)** Reject $H_0$ if $F > 4.26$ ($df_1 = 2, df_2 = 9$).

**(c)** $\text{SST} = 107.20$, $\text{SSE} = 9.47$, $\text{SS total} = 116.67$.

**(d) ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 107.20 | 2 | 53.600 | 50.96 |
| Error | 9.47 | 9 | 1.052 | |
| Total | 116.67 | 11 | | |

**(e)** **Reject $H_0$** because $F = 50.96 > 4.26$. At least one pair of treatment means differs.

**(f)** 95% confidence interval for $\mu_{1} - \mu_{2}$ ($t_{.025, 9} = 2.262$):
$$(\bar{X}_{1} - \bar{X}_{2}) \pm t\sqrt{\text{MSE}\left(\frac{1}{n_{1}} + \frac{1}{n_{2}}\right)} = (9.667 - 2.200) \pm 2.262\sqrt{1.052\left(\frac{1}{3} + \frac{1}{5}\right)} = 7.467 \pm 1.694 = [5.772,\; 9.161]$$
Yes, treatments 1 and 2 differ significantly because 0 is not in the interval.

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 4.26$) and Appendix B.2 ($t_{\text{crit}} = 2.262$).*

**Answer:** $\text{SST} = 107.20, \text{SSE} = 9.47, \text{SS total} = 116.67, F = 50.96$ (reject $H_0$); 95% CI $= [5.772, 9.161]$ (differ).

✔ *Checker: Exact scipy $F = 50.9577, p = 0.000012$.*

---

### Exercise 12.12
**Problem:** Given the following sample information: Treatment 1 (`3, 2, 5, 1, 3, 1`), Treatment 2 (`9, 6, 5, 6, 8, 5, 4, 7, 6, 4`), and Treatment 3 (`6, 3, 5, 5, 5, 4, 1, 5`), test the hypothesis that the treatment means are equal at the .05 significance level.
(a) State the null hypothesis and the alternate hypothesis.
(b) What is the decision rule?
(c) Compute SST, SSE, and SS total.
(d) Complete an ANOVA table.
(e) State your decision regarding the null hypothesis.
(f) If $H_0$ is rejected, can we conclude that treatment 2 and treatment 3 differ? Use the 95 percent level of confidence.

**Given:** $k = 3$ treatments ($n_1 = 6, n_2 = 10, n_3 = 8$, total $n = 24$), $\alpha = .05$.

**(a)** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.

**(b)** Reject $H_0$ if $F > 3.47$ ($df_1 = 2, df_2 = 21$).

**(c)** $\text{SST} = 46.96$, $\text{SSE} = 53.00$, $\text{SS total} = 99.96$.

**(d) ANOVA Table:**

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 46.96 | 2 | 23.479 | 9.30 |
| Error | 53.00 | 21 | 2.524 | |
| Total | 99.96 | 23 | | |

**(e)** **Reject $H_0$** because $F = 9.30 > 3.47$. At least one pair of treatment means differs.

**(f)** 95% confidence interval for $\mu_{2} - \mu_{3}$ ($t_{.025, 21} = 2.080$):
$$(\bar{X}_{2} - \bar{X}_{3}) \pm t\sqrt{\text{MSE}\left(\frac{1}{n_{2}} + \frac{1}{n_{3}}\right)} = (6.000 - 4.250) \pm 2.080\sqrt{2.524\left(\frac{1}{10} + \frac{1}{8}\right)} = 1.750 \pm 1.567 = [0.183,\; 3.317]$$
Yes, treatments 2 and 3 differ significantly because 0 is not in the interval.

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.47$) and Appendix B.2 ($t_{\text{crit}} = 2.080$).*

**Answer:** $\text{SST} = 46.96, \text{SSE} = 53.00, \text{SS total} = 99.96, F = 9.30$ (reject $H_0$); 95% CI $= [0.183, 3.317]$ (differ).

✔ *Checker: Exact scipy $F = 9.3031, p = 0.001279$.*

---

### Exercise 12.13
**Problem:** A senior accounting major at Midsouth State University has job offers from four CPA firms. To explore the offers further, she asked a sample of recent trainees how many months each worked for the firm before receiving a raise in salary. The Minitab ANOVA output shows: Factor ($DF=3, SS=32.33, MS=10.78, F=2.36, P=0.133$), Error ($DF=10, SS=45.67, MS=4.57$), Total ($DF=13, SS=78.00$). At the .05 level of significance, is there a difference in the mean number of months before a raise was granted among the four CPA firms?

**Given:** $k = 4$ CPA firms ($df_1 = 3, df_2 = 10$), $F = 2.36$, $p\text{-value} = .133$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$ versus $H_1:$ Not all means are equal.
- **Decision rule ($df_1 = 3, df_2 = 10, \alpha = .05$):** Reject $H_0$ if $F > 3.71$.
- **Decision:** Since $F = 2.36 < 3.71$ (and $p = .133 > .05$), **do not reject $H_0$**. There is no significant difference in the mean number of months before a raise among the four CPA firms.

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 10, \alpha = .05 \implies F_{\text{crit}} = 3.71$).*

**Answer:** Reject $H_0$ if $F > 3.71$; since $F = 2.36 < 3.71$, do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.14
**Problem:** A stock analyst wants to determine whether there is a difference in the mean rate of return for three types of stock: utility, retail, and banking stocks. The Minitab output shows: Factor ($DF=2, SS=86.49, MS=43.25, F=13.09, P=0.001$), Error ($DF=13, SS=42.95, MS=3.30$), Total ($DF=15, SS=129.44$); Utility ($N=5, \text{Mean}=17.400, \text{StDev}=1.916$), Retail ($N=5, \text{Mean}=11.620, \text{StDev}=0.356$), Banking ($N=6, \text{Mean}=15.400, \text{StDev}=2.356$), Pooled StDev $= 1.818$.
(a) Using the .05 level of significance, is there a difference in the mean rate of return among the three types of stock?
(b) Suppose the null hypothesis is rejected. Can the analyst conclude there is a difference between the mean rates of return for the utility and the retail stocks? Explain.

**Given:** $k = 3$ stock types ($df_1 = 2, df_2 = 13$), $F = 13.09$, $p\text{-value} = .001$, $\text{MSE} = 3.30$, $\alpha = .05$.

**(a)**
- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
- **Decision rule ($df_1 = 2, df_2 = 13, \alpha = .05$):** Reject $H_0$ if $F > 3.81$.
- **Decision:** Since $F = 13.09 > 3.81$ (and $p = .001 < .05$), **reject $H_0$**. There is a significant difference in the mean rate of return among the three types of stock.

**(b)** Using formula [12–5] for Utility ($n_1 = 5, \bar{X}_1 = 17.400$) versus Retail ($n_2 = 5, \bar{X}_2 = 11.620$) with $df = 13$ ($t_{.025, 13} = 2.160$) and $\text{MSE} = 3.30$:
$$(17.400 - 11.620) \pm 2.160\sqrt{3.30\left(\frac{1}{5} + \frac{1}{5}\right)} = 5.780 \pm 2.160(1.1489) = 5.780 \pm 2.482 = [3.298,\; 8.262]$$
Because both endpoints are positive (the 95% confidence intervals in the Minitab printout do not overlap and 0 is not in $[3.30, 8.26]$), **yes**, the mean rates of return for utility and retail stocks differ significantly.

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.81$) and Appendix B.2 ($t_{.025, 13} = 2.160$).*

**Answer:** (a) $F = 13.09 > 3.81$, reject $H_0$; (b) yes, 95% CI for $\mu_{\text{Utility}} - \mu_{\text{Retail}}$ is $[3.30, 8.26]$ (does not contain 0, and individual CIs do not overlap).

✔ *Checker: Exact scipy $p = 0.000769$.*

---

## Lind — Chapter 12, Section 12.7: Two-Way Analysis of Variance

### Exercise 12.15
**Problem:** Conduct a two-factor ANOVA (without replication) at the .05 significance level for Treatments 1 and 2 across Blocks A (`46, 31`), B (`37, 26`), and C (`44, 35`).
(a) State the null and alternate hypotheses for treatments.
(b) State the decision rule for treatments.
(c) State the null and alternate hypotheses for blocks, and the decision rule for blocks.
(d) Compute SST, SSB, SS total, and SSE.
(e) Complete an ANOVA table.
(f) Give your decision regarding the two sets of hypotheses.

**Given:** $k = 2$ treatments, $b = 3$ blocks, $n = 6$, $\alpha = .05$.

- **Hypotheses & Decision rules:**
  - Treatments ($df_1 = 1, df_2 = 2$): $H_0: \mu_1 = \dots = \mu_2$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 18.50$.
  - Blocks ($df_1 = 2, df_2 = 2$): $H_0: \mu_{B1} = \dots = \mu_{B3}$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 19.00$.
- **Sums of squares:** $\text{SST} = 204.167$, $\text{SSB} = 76.000$, $\text{SSE} = 9.333$, $\text{SS total} = 289.500$.
- **ANOVA Table:**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 204.167 | 1 | 204.167 | 43.75 | 0.0221 |
| Blocks | 76.000 | 2 | 38.000 | 8.14 | 0.1094 |
| Error | 9.333 | 2 | 4.667 | | |
| Total | 289.500 | 5 | | | |

- **Decisions:** **Reject $H_0$ for treatments** ($F = 43.75 ('>' if rej else '<=') 18.50$); **Do not reject $H_0$ for blocks** ($F = 8.14 ('>' if rej else '<=') 19.00$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit, treat}} = 18.50, F_{\text{crit, block}} = 19.00$).*

**Answer:** $\text{SST} = 204.167, \text{SSB} = 76.000, \text{SSE} = 9.333, \text{SS total} = 289.500$; $F_{\text{treat}} = 43.75$ (Reject $H_0$ for treatments), $F_{\text{block}} = 8.14$ (Do not reject $H_0$ for blocks).

✔ *Checker: Exact scipy $p_{\text{treat}} = 0.022102, p_{\text{block}} = 0.109375$.*

---

### Exercise 12.16
**Problem:** Conduct a two-factor ANOVA (without replication) at the .05 significance level for Treatments 1, 2, and 3 across Blocks A (`12, 14, 8`), B (`9, 11, 9`), and C (`7, 8, 8`).
(a) State the null and alternate hypotheses for treatments.
(b) State the decision rule for treatments.
(c) State the null and alternate hypotheses for blocks, and the decision rule for blocks.
(d) Compute SST, SSB, SS total, and SSE.
(e) Complete an ANOVA table.
(f) Give your decision regarding the two sets of hypotheses.

**Given:** $k = 3$ treatments, $b = 3$ blocks, $n = 9$, $\alpha = .05$.

- **Hypotheses & Decision rules:**
  - Treatments ($df_1 = 2, df_2 = 4$): $H_0: \mu_1 = \dots = \mu_3$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 6.94$.
  - Blocks ($df_1 = 2, df_2 = 4$): $H_0: \mu_{B1} = \dots = \mu_{B3}$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 6.94$.
- **Sums of squares:** $\text{SST} = 10.889$, $\text{SSB} = 20.222$, $\text{SSE} = 11.111$, $\text{SS total} = 42.222$.
- **ANOVA Table:**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 10.889 | 2 | 5.444 | 1.96 | 0.2551 |
| Blocks | 20.222 | 2 | 10.111 | 3.64 | 0.1257 |
| Error | 11.111 | 4 | 2.778 | | |
| Total | 42.222 | 8 | | | |

- **Decisions:** **Do not reject $H_0$ for treatments** ($F = 1.96 ('>' if rej else '<=') 6.94$); **Do not reject $H_0$ for blocks** ($F = 3.64 ('>' if rej else '<=') 6.94$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit, treat}} = 6.94, F_{\text{crit, block}} = 6.94$).*

**Answer:** $\text{SST} = 10.889, \text{SSB} = 20.222, \text{SSE} = 11.111, \text{SS total} = 42.222$; $F_{\text{treat}} = 1.96$ (Do not reject $H_0$ for treatments), $F_{\text{block}} = 3.64$ (Do not reject $H_0$ for blocks).

✔ *Checker: Exact scipy $p_{\text{treat}} = 0.255076, p_{\text{block}} = 0.125748$.*

---

### Exercise 12.17
**Problem:** Chapin Manufacturing Company recorded output for a sample of five workers across three shifts (Day, Afternoon, Night): Skaff (`31, 25, 35`), Lum (`33, 26, 33`), Clark (`28, 24, 30`), Treece (`30, 29, 28`), and Morgan (`28, 26, 27`). At the .05 significance level, can we conclude there is a difference in the mean production rate by shift or by employee?

**Given:** $k = 3$ treatments, $b = 5$ blocks, $n = 15$, $\alpha = .05$.

- **Hypotheses & Decision rules:**
  - Treatments ($df_1 = 2, df_2 = 8$): $H_0: \mu_1 = \dots = \mu_3$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 4.46$.
  - Blocks ($df_1 = 4, df_2 = 8$): $H_0: \mu_{B1} = \dots = \mu_{B5}$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 3.84$.
- **Sums of squares:** $\text{SST} = 62.533$, $\text{SSB} = 33.733$, $\text{SSE} = 43.467$, $\text{SS total} = 139.733$.
- **ANOVA Table:**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 62.533 | 2 | 31.267 | 5.75 | 0.0283 |
| Blocks | 33.733 | 4 | 8.433 | 1.55 | 0.2762 |
| Error | 43.467 | 8 | 5.433 | | |
| Total | 139.733 | 14 | | | |

- **Decisions:** **Reject $H_0$ for treatments** ($F = 5.75 ('>' if rej else '<=') 4.46$); **Do not reject $H_0$ for blocks** ($F = 1.55 ('>' if rej else '<=') 3.84$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit, treat}} = 4.46, F_{\text{crit, block}} = 3.84$).*

**Answer:** $\text{SST} = 62.533, \text{SSB} = 33.733, \text{SSE} = 43.467, \text{SS total} = 139.733$; $F_{\text{treat}} = 5.75$ (Reject $H_0$ for treatments), $F_{\text{block}} = 1.55$ (Do not reject $H_0$ for blocks).

✔ *Checker: Exact scipy $p_{\text{treat}} = 0.028275, p_{\text{block}} = 0.276152$.*

---

### Exercise 12.18
**Problem:** The following data show the number of outpatient surgeries performed at three hospitals in Tulsa, Oklahoma (St. Luke's, St. Vincent, Mercy) across five days: Monday (`14, 18, 24`), Tuesday (`20, 24, 14`), Wednesday (`16, 22, 14`), Thursday (`18, 20, 22`), and Friday (`20, 28, 24`). At the .05 significance level, can we conclude there is a difference in the mean number of surgeries performed by hospital or by day of the week?

**Given:** $k = 3$ treatments, $b = 5$ blocks, $n = 15$, $\alpha = .05$.

- **Hypotheses & Decision rules:**
  - Treatments ($df_1 = 2, df_2 = 8$): $H_0: \mu_1 = \dots = \mu_3$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 4.46$.
  - Blocks ($df_1 = 4, df_2 = 8$): $H_0: \mu_{B1} = \dots = \mu_{B5}$ vs. $H_1:$ Not all equal. Reject $H_0$ if $F > 3.84$.
- **Sums of squares:** $\text{SST} = 58.133$, $\text{SSB} = 75.733$, $\text{SSE} = 117.867$, $\text{SS total} = 251.733$.
- **ANOVA Table:**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 58.133 | 2 | 29.067 | 1.97 | 0.2011 |
| Blocks | 75.733 | 4 | 18.933 | 1.29 | 0.3524 |
| Error | 117.867 | 8 | 14.733 | | |
| Total | 251.733 | 14 | | | |

- **Decisions:** **Do not reject $H_0$ for treatments** ($F = 1.97 ('>' if rej else '<=') 4.46$); **Do not reject $H_0$ for blocks** ($F = 1.29 ('>' if rej else '<=') 3.84$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit, treat}} = 4.46, F_{\text{crit, block}} = 3.84$).*

**Answer:** $\text{SST} = 58.133, \text{SSB} = 75.733, \text{SSE} = 117.867, \text{SS total} = 251.733$; $F_{\text{treat}} = 1.97$ (Do not reject $H_0$ for treatments), $F_{\text{block}} = 1.29$ (Do not reject $H_0$ for blocks).

✔ *Checker: Exact scipy $p_{\text{treat}} = 0.201147, p_{\text{block}} = 0.352359$.*

---

## Lind — Chapter 12, Section 12.8: Two-Way ANOVA with Interaction

### Exercise 12.19
**Problem:** Consider the sample data for a two-factor ANOVA experiment with Weight (Heavy vs. Light) and Size (Small, Medium, Large): Heavy-Small (`23, 21, 25`), Heavy-Medium (`20, 32, 26`), Heavy-Large (`11, 20, 20`), Light-Small (`13, 32, 17`), Light-Medium (`20, 17, 15`), Light-Large (`11, 23, 8`). Use the .05 significance level to answer:
(a) Is there a difference in the Size means?
(b) Is there a difference in the Weight means?
(c) Is there a significant interaction between Weight and Size?

**Given:** $k = 3$ Size levels, $b = 2$ Weight levels, $r = 3$ replications per cell ($n = 18$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Size | 156.333 | 2 | 78.1667 | 1.98 | 0.180 | 3.89 |
| Weight | 98.000 | 1 | 98.0000 | 2.48 | 0.141 | 4.75 |
| Interaction | 36.333 | 2 | 18.1667 | 0.46 | 0.642 | 3.89 |
| Error | 473.333 | 12 | 39.4444 | | | |
| Total | 764.000 | 17 | | | | |

**(a)** Since $F = 1.98 < 3.89$ ($p = 0.180 > .05$), **no**, there is no significant difference in the Size means.

**(b)** Since $F = 2.48 < 4.75$ ($p = 0.141 > .05$), **no**, there is no significant difference in the Weight means.

**(c)** Since $F = 0.46 < 3.89$ ($p = 0.642 > .05$), **no**, there is no significant interaction between Weight and Size.

📘 *Table used: Lind Appendix B.4 ($df = (2,12) \implies 3.89$; $df = (1,12) \implies 4.75$).*

**Answer:** (a) No ($F = 1.98, p = .180$); (b) No ($F = 2.48, p = .141$); (c) No ($F = 0.46, p = .642$).

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.20
**Problem:** Consider the partially completed two-way ANOVA table: Factor A ($SS = 75$), Factor B ($SS = 25$), Interaction ($SS = 300$), Error ($SS = 600$), Total ($SS = 1000$). Suppose there are four levels of Factor A and three levels of Factor B. The number of replications per cell is 5. Complete the table and test to determine if there is a significant difference in Factor A means, Factor B means, or the interaction means. Use the .05 significance level.

**Given:** $k = 4$ levels of Factor A, $b = 3$ levels of Factor B, $r = 5$ replications per cell ($n = 4 \times 3 \times 5 = 60$).

- **Degrees of freedom:** $df_A = 4 - 1 = 3$, $df_B = 3 - 1 = 2$, $df_I = 3 \times 2 = 6$, $df_E = 60 - 12 = 48$, $df_{\text{Total}} = 59$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Factor A | 75 | 3 | 25.00 | 2.00 | 0.1265 | 2.80 |
| Factor B | 25 | 2 | 12.50 | 1.00 | 0.3754 | 3.19 |
| Interaction | 300 | 6 | 50.00 | 4.00 | 0.0025 | 2.30 |
| Error | 600 | 48 | 12.50 | | | |
| Total | 1000 | 59 | | | | |

- **Decisions ($\alpha = .05$):**
  - **Factor A:** $F = 2.00 < 2.80 \implies$ **Do not reject $H_0$** (Factor A means do not differ significantly).
  - **Factor B:** $F = 1.00 < 3.19 \implies$ **Do not reject $H_0$** (Factor B means do not differ significantly).
  - **Interaction:** $F = 4.00 > 2.30 \implies$ **Reject $H_0$** (there is a significant interaction between Factor A and Factor B).

📘 *Table used: Lind Appendix B.4 ($df_E = 48$).*

**Answer:** $F_A = 2.00$ (not significant), $F_B = 1.00$ (not significant), $F_I = 4.00 > 2.30$ (significant interaction).

✔ *Checker: Exact scipy $p_A = 0.1265, p_B = 0.3754, p_I = 0.0025$.*

---

### Exercise 12.21
**Problem:** The distributor of the Wapakoneta Daily News is considering three types of dispensing machines (`J-1000`, `D-320`, `UV-57`) and two positions (`Inside`, `Outside`): Inside J-1000 (`33, 40, 30, 31`), Inside D-320 (`29, 28, 33, 33`), Inside UV-57 (`47, 39, 39, 45`), Outside J-1000 (`43, 36, 41, 40`), Outside D-320 (`48, 45, 40, 44`), Outside UV-57 (`37, 32, 36, 35`).
(a) Draw the interaction graph. Based on your observations, is there an interaction effect?
(b) Use the 0.05 level to test for position, machine, and interaction effects on sales.
(c) Compare the inside and outside mean sales for each machine using statistical techniques. What do you conclude?

**Given:** $b = 2$ Positions, $k = 3$ Machines, $r = 4$ days per cell ($n = 24$), $\alpha = .05$.

**(a) Cell means & Interaction plot:**
- Inside means: J-1000 $= 33.50$, D-320 $= 30.75$, UV-57 $= 42.50$.
- Outside means: J-1000 $= 40.00$, D-320 $= 44.25$, UV-57 $= 35.00$.
- The Inside and Outside lines cross sharply between D-320 and UV-57: J-1000 and D-320 sell more Outside, whereas UV-57 sells more Inside. This indicates a strong interaction effect.

**(b) Two-way ANOVA Table:**

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Position | 104.167 | 1 | 104.167 | 9.12 | 0.007 | 4.41 |
| Machine | 16.333 | 2 | 8.167 | 0.72 | 0.502 | 3.55 |
| Interaction | 457.333 | 2 | 228.667 | 20.03 | 0.000 | 3.55 |
| Error | 205.500 | 18 | 11.417 | | | |
| Total | 783.333 | 23 | | | | |

- **Position** ($F = 9.12, p = .007$) and **Interaction** ($F = 20.03, p = .000$) are statistically significant at $\alpha = .05$; **Machine** main effect ($F = 0.72, p = .502$) is not significant.

**(c) One-way ANOVAs by Machine (Inside vs. Outside, $df = (1, 6), F_{\text{crit}} = 5.99$):**
- **J-1000:** $\text{SS}_{\text{Pos}} = 84.50, \text{SSE} = 87.00, \text{MSE} = 14.50, F = 5.83, p = .052 > .05$ (not statistically significant at .05; position does not significantly matter for J-1000).
- **D-320:** $\text{SS}_{\text{Pos}} = 364.50, \text{SSE} = 53.50, \text{MSE} = 8.92, F = 40.88, p = .001 < .05$ (significant: position D-320 **Outside** where mean $= 44.25$ vs. $30.75$).
- **UV-57:** $\text{SS}_{\text{Pos}} = 112.50, \text{SSE} = 65.00, \text{MSE} = 10.83, F = 10.38, p = .018 < .05$ (significant: position UV-57 **Inside** where mean $= 42.50$ vs. $35.00$).

📘 *Table used: Lind Appendix B.4 ($df = (1,18) \implies 4.41, df = (2,18) \implies 3.55, df = (1,6) \implies 5.99$).*

**Answer:** (a) Yes, strong interaction; (b) $F_{\text{Pos}} = 9.12 (p=.007)$, $F_{\text{Mach}} = 0.72 (p=.502)$, $F_{\text{Inter}} = 20.03 (p=.000)$; (c) place D-320 Outside ($F=40.88, p=.001$), place UV-57 Inside ($F=10.38, p=.018$), and J-1000 position is not significant ($F=5.83, p=.052$).

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.22
**Problem:** A large company is organized into three functional areas (Manufacturing, Marketing, Research and Development) and recorded weekly salaries ($) for 4 Females and 4 Males in each area: Manufacturing Female (`1016, 1007, 875, 968`), Manufacturing Male (`978, 1056, 982, 748`), Marketing Female (`1045, 895, 848, 904`), Marketing Male (`1154, 1091, 878, 876`), R&D Female (`770, 733, 844, 771`), R&D Male (`926, 1055, 1066, 1088`).
(a) Draw the interaction graph. Based on your observations, is there an interaction effect?
(b) Use the 0.05 level to test for gender, area, and interaction effects on salary.
(c) Compare the male and female mean salaries for each area using statistical techniques. What do you recommend?

**Given:** $b = 3$ Areas, $k = 2$ Genders, $r = 4$ employees per cell ($n = 24$), $\alpha = .05$.

**(a) Cell means & Interaction plot:**
- Manufacturing: Female $= \$966.50$, Male $= \$941.00$.
- Marketing: Female $= \$923.00$, Male $= \$999.75$.
- R&D: Female $= \$779.50$, Male $= \$1,033.75$.
- The gender lines cross between Manufacturing and Marketing and diverge sharply in R&D, indicating an interaction between Area and Gender.

**(b) Two-way ANOVA Table:**

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Gender | 62220.17 | 1 | 62220.17 | 6.50 | 0.0202 | 4.41 |
| Area | 14070.58 | 2 | 7035.29 | 0.73 | 0.4936 | 3.55 |
| Interaction | 80147.58 | 2 | 40073.79 | 4.18 | 0.0322 | 3.55 |
| Error | 172429.50 | 18 | 9579.42 | | | |
| Total | 328867.83 | 23 | | | | |

- **Gender** ($F = 6.50, p = 0.0202 < .05$) and **Interaction** ($F = 4.18, p = 0.0322 < .05$) are statistically significant; **Area** ($F = 0.73, p = 0.4936 > .05$) is not significant.

**(c) One-way ANOVAs by Area (Female vs. Male, $df = (1, 6), F_{\text{crit}} = 5.99$):**
- **Manufacturing:** $F = 0.11, p = .752$ (no significant difference: $\$966.50$ vs. $\$941.00$).
- **Marketing:** $F = 0.85, p = .392$ (no significant difference: $\$923.00$ vs. $\$999.75$).
- **Research & Development:** $F = 32.33, p = .0013 < .05$ (highly significant difference: R&D females earn $\$779.50$ vs. R&D males $\$1,033.75$).
- **Recommendation:** Investigate and remedy the salary disparity between male and female employees in the Research and Development department.

📘 *Table used: Lind Appendix B.4 ($df = (1,18) \implies 4.41, df = (2,18) \implies 3.55, df = (1,6) \implies 5.99$).*

**Answer:** (a) Interaction present; (b) $F_{\text{Gender}} = 6.50 (p=0.0202)$, $F_{\text{Area}} = 0.73 (p=0.4936)$, $F_{\text{Inter}} = 4.18 (p=0.0322)$; (c) only R&D shows a significant gender gap ($F = 32.33, p = .0013$).

✔ *Checker: Exact scipy two-way and one-way ANOVA values verified.*

---

## Lind — Chapter 12: Chapter Exercises

### Exercise 12.23
**Problem:** A real estate agent in the coastal area of Georgia wants to compare the variation in the selling price of homes on the oceanfront ($n_1 = 21, s_1 = \$45,600$) with those one to three blocks from the ocean ($n_2 = 18, s_2 = \$21,330$). At the .01 significance level, can we conclude that there is more variation in the selling prices of the oceanfront homes?

**Given:** $n_1 = 21$ ($df_1 = 20$), $s_1 = 45,600$; $n_2 = 18$ ($df_2 = 17$), $s_2 = 21,330$; $\alpha = .01$.

- **Hypotheses:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$.
- **Decision rule ($df_1 = 20, df_2 = 17, \alpha = .01$):** Reject $H_0$ if $F > 3.16$.
- **Test statistic:**
$$F = \frac{(45,600)^2}{(21,330)^2} = 4.57$$
- **Decision:** **Reject $H_0$** ($F = 4.57 > 3.16$). There is significantly more variation in the selling prices of oceanfront homes.

📘 *Table used: Lind Appendix B.4 ($df_1 = 20, df_2 = 17, \alpha = .01 \implies 3.16$).*

**Answer:** $F = 4.57 > 3.16$; reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.24
**Problem:** A sample of 16 computer runs showed that the standard deviation of the processing time was 22 (hundredths of a second) for the new machine and 12 (hundredths of a second) for the current machine ($n_1 = 16, n_2 = 16$). At the .05 significance level can we conclude that there is more variation in the processing time of the new machine?

**Given:** $n_1 = 16$ ($df_1 = 15$), $s_1 = 22$; $n_2 = 16$ ($df_2 = 15$), $s_2 = 12$; $\alpha = .05$.

- **Hypotheses:** $H_0: \sigma_1^2 \le \sigma_2^2$ versus $H_1: \sigma_1^2 > \sigma_2^2$.
- **Decision rule ($df_1 = 15, df_2 = 15, \alpha = .05$):** Reject $H_0$ if $F > 2.40$.
- **Test statistic:**
$$F = \frac{22^2}{12^2} = \frac{484}{144} = 3.36$$
- **Decision:** **Reject $H_0$** ($F = 3.36 > 2.40$). There is significantly more variation in the processing time of the new machine.

📘 *Table used: Lind Appendix B.4 ($df_1 = 15, df_2 = 15, \alpha = .05 \implies 2.40$).*

**Answer:** $F = 3.36 > 2.40$; reject $H_0$.

✔ *Checker: Exact scipy $F = 3.3611, p = 0.013019$.*

---

### Exercise 12.25
**Problem:** Tom Sharkey, owner of Sharkey Chevy (`98, 78, 54, 57, 68, 64, 70`, $n_s=7$), believes his monthly car sales are more consistent than Dave White Chevrolet (`75, 81, 81, 30, 82, 46, 58, 101`, $n_w=8$). Do you agree with Mr. Sharkey? Use the .01 significance level.

**Given:** Dave White: $n_w = 8$ ($df_w = 7$), $s_w = 22.95$; Sharkey: $n_s = 7$ ($df_s = 6$), $s_s = 14.79$; $\alpha = .01$.

- **Hypotheses:** $H_0: \sigma_w^2 \le \sigma_s^2$ versus $H_1: \sigma_w^2 > \sigma_s^2$.
- **Decision rule ($df_1 = 7, df_2 = 6, \alpha = .01$):** Reject $H_0$ if $F > 8.26$.
- **Test statistic:**
$$F = \frac{s_w^2}{s_s^2} = \frac{(22.95)^2}{(14.79)^2} = \frac{526.79}{218.81} = 2.41$$
- **Decision:** **Do not reject $H_0$** ($F = 2.41 < 8.26$). We cannot conclude that Sharkey's sales are more consistent.

📘 *Table used: Lind Appendix B.4 ($df_1 = 7, df_2 = 6, \alpha = .01 \implies 8.26$).*

**Answer:** $s_w = 22.95, s_s = 14.79, F = 2.41 < 8.26$; do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.26
**Problem:** Random samples of five were selected from each of three populations. The sum of squares total was 100. The sum of squares due to the treatments was 40.
(a) Set up the null hypothesis and the alternate hypothesis.
(b) What is the decision rule? Use the .05 significance level.
(c) Complete the ANOVA table. What is the value of F?
(d) What is your decision regarding the null hypothesis?

**Given:** $k = 3$, $n = 3 \times 5 = 15$ ($df_1 = 2, df_2 = 12$), $\text{SS total} = 100$, $\text{SST} = 40$, $\text{SSE} = 60$, $\alpha = .05$.

**(a)** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.

**(b)** Reject $H_0$ if $F > 3.89$ ($df_1 = 2, df_2 = 12, \alpha = .05$).

**(c) ANOVA Table:** $\text{MST} = 40/2 = 20.0$, $\text{MSE} = 60/12 = 5.0$, $F = 20.0/5.0 = 4.00$.

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 40 | 2 | 20.0 | 4.00 |
| Error | 60 | 12 | 5.0 | |
| Total | 100 | 14 | | |

**(d)** **Reject $H_0$** because $F = 4.00 > 3.89$. The population means are not all equal.

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 12, \alpha = .05 \implies 3.89$).*

**Answer:** (a) $H_0: \mu_1 = \mu_2 = \mu_3$; (b) reject $H_0$ if $F > 3.89$; (c) $F = 4.00$; (d) reject $H_0$.

✔ *Checker: Exact scipy $p = 0.04666$.*

---

### Exercise 12.27
**Problem:** In an ANOVA table, MSE was equal to 10. Random samples of six were selected from each of four populations, where the sum of squares total was 250.
(a) Set up the null hypothesis and the alternate hypothesis.
(b) What is the decision rule? Use the .05 significance level.
(c) Complete the ANOVA table. What is the value of F?
(d) What is your decision regarding the null hypothesis?

**Given:** $k = 4$, $n = 4 \times 6 = 24$ ($df_1 = 3, df_2 = 20$), $\text{MSE} = 10 \implies \text{SSE} = 20 \times 10 = 200$, $\text{SS total} = 250 \implies \text{SST} = 50$, $\alpha = .05$.

**(a)** $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$ versus $H_1:$ Treatment means are not all equal.

**(b)** Reject $H_0$ if $F > 3.10$ ($df_1 = 3, df_2 = 20, \alpha = .05$).

**(c) ANOVA Table:** $\text{MST} = 50/3 = 16.67$, $\text{MSE} = 10.00$, $F = 16.67/10 = 1.67$.

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatments | 50 | 3 | 16.67 | 1.67 |
| Error | 200 | 20 | 10.00 | |
| Total | 250 | 23 | | |

**(d)** **Do not reject $H_0$** because $F = 1.67 < 3.10$.

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 20, \alpha = .05 \implies 3.10$).*

**Answer:** (a) $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$; (b) reject $H_0$ if $F > 3.10$; (c) $F = 1.67$; (d) do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.28
**Problem:** Complete the partial ANOVA table (Treatment $df = 2$, Error $MS = 20$, Total $SS = 500, df = 11$) and answer at the .05 significance level:
(a) How many treatments are there?
(b) What is the total sample size?
(c) What is the critical value of F?
(d) Write out the null and alternate hypotheses.
(e) What is your conclusion regarding the null hypothesis?

**Given:** $df_1 = k - 1 = 2 \implies k = 3$; $df_{\text{Total}} = n - 1 = 11 \implies n = 12$; $df_2 = 11 - 2 = 9$; $\text{MSE} = 20 \implies \text{SSE} = 9 \times 20 = 180$; $\text{SST} = 500 - 180 = 320 \implies \text{MST} = 320/2 = 160$; $F = 160/20 = 8.00$.

| Source | SS | df | MS | F |
|---|---|---|---|---|
| Treatment | 320 | 2 | 160 | 8.00 |
| Error | 180 | 9 | 20 | |
| Total | 500 | 11 | | |

**(a)** $k = 3$ treatments.
**(b)** $n = 12$ observations.
**(c)** From Appendix B.4 ($df_1 = 2, df_2 = 9, \alpha = .05$), $F_{\text{crit}} = 4.26$.
**(d)** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all treatment means are equal.
**(e)** **Reject $H_0$** because $F = 8.00 > 4.26$. The treatment means differ significantly.

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 9, \alpha = .05 \implies 4.26$).*

**Answer:** (a) 3; (b) 12; (c) 4.26; (d) $H_0: \mu_1 = \mu_2 = \mu_3$; (e) $F = 8.00 > 4.26$, reject $H_0$.

✔ *Checker: Exact scipy $p = 0.01007$.*

---

### Exercise 12.29
**Problem:** A consumer organization checked the price of a toy at five Discount stores (`12, 13, 14, 12, 15`), five Variety stores (`15, 17, 14, 18, 17`), and five Department stores (`19, 17, 16, 20, 19`). Use the .05 significance level to test whether there is a difference in the mean prices.

**Given:** $k = 3$ groups, $n = 15$ total observations ($df_1 = 2, df_2 = 12$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 63.33 | 2 | 31.667 | 13.38 | 0.0009 |
| Error | 28.40 | 12 | 2.367 | | |
| Total | 91.73 | 14 | | | |

- **Decision rule:** Reject $H_0$ if $F > 3.89$.
- **Decision:** **Reject $H_0$** ($F = 13.38 ('>' if rej else '<=') 3.89$).

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 12, \alpha = .05 \implies 3.89$).*

**Answer:** $\text{SST} = 63.33, \text{SSE} = 28.40, F = 13.38$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 13.3803, p = 0.000881$.*

---

### Exercise 12.30
**Problem:** Jacob Lee recorded flight times between Los Angeles and San Francisco on three airlines: Goust (`51, 51, 52, 42, 51, 57, 47, 47, 50, 60, 54, 49, 48, 48`), Jet Red (`50, 53, 52, 62, 53, 49, 50, 49, 58, 54, 51, 49, 49, 50`), and Cloudtran (`52, 55, 60, 64, 61, 49, 49`).
(a) Use the .05 significance level to check if there is a difference in the mean flight times among the three airlines.
(b) Develop a 95 percent confidence interval for the difference in the means between Goust and Cloudtran.

**Given:** $k = 3$ groups, $n = 35$ total observations ($df_1 = 2, df_2 = 32$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 127.11 | 2 | 63.557 | 3.04 | 0.0620 |
| Error | 669.86 | 32 | 20.933 | | |
| Total | 796.97 | 34 | | | |

- **Decision rule:** Reject $H_0$ if $F > 3.30$.
- **Decision:** **Do not reject $H_0$** ($F = 3.04 ('>' if rej else '<=') 3.30$).
- **(b) 95% CI for $\mu_{\text{Goust}} - \mu_{\text{Cloudtran}}$ ($df = 32, t = 2.037$):** $(50.500 - 55.714) \pm 2.037\sqrt{20.933(1/14 + 1/7)} = -5.214 \pm 4.314 = [-9.529,\; -0.900]$. Since both endpoints are negative, Goust has a significantly shorter mean flight time than Cloudtran.

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 32, \alpha = .05 \implies 3.30$).*

**Answer:** $\text{SST} = 127.11, \text{SSE} = 669.86, F = 3.04$; Do not reject $H_0$.

✔ *Checker: Exact scipy $F = 3.0362, p = 0.062034$.*

---

### Exercise 12.31
**Problem:** The City of Maumee recorded the number of crimes in four districts over six days: Rec Center (`13, 15, 14, 15, 14, 15`), Key Street (`21, 13, 18, 19, 18, 19`), Monclova (`12, 14, 15, 13, 12, 15`), and Whitehouse (`16, 17, 18, 15, 20, 18`). At the .05 significance level, can the chief of police conclude there is a difference in the mean number of crimes?

**Given:** $k = 4$ groups, $n = 24$ total observations ($df_1 = 3, df_2 = 20$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 87.79 | 3 | 29.264 | 9.12 | 0.0005 |
| Error | 64.17 | 20 | 3.208 | | |
| Total | 151.96 | 23 | | | |

- **Decision rule:** Reject $H_0$ if $F > 3.10$.
- **Decision:** **Reject $H_0$** ($F = 9.12 ('>' if rej else '<=') 3.10$).

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 20, \alpha = .05 \implies 3.10$).*

**Answer:** $\text{SST} = 87.79, \text{SSE} = 64.17, F = 9.12$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 9.1212, p = 0.000523$.*

---

### Exercise 12.32
**Problem:** A study measured the attention span (in seconds) of 12-year-old children for commercials for Clothes (`26, 21, 43, 35, 28, 31, 17, 31, 20`), Food (`45, 48, 43, 53, 47, 42, 34, 43, 57, 47, 44, 54`), and Toys (`60, 51, 43, 54, 63, 53, 48, 58, 47, 51, 51`). At the .05 significance level, is there a difference in the mean attention span? Are there significant differences between pairs of means? Would you recommend dropping one of the three commercial types?

**Given:** $k = 3$ groups, $n = 32$ total observations ($df_1 = 2, df_2 = 29$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 3182.04 | 2 | 1591.019 | 35.56 | 0.0000 |
| Error | 1297.46 | 29 | 44.740 | | |
| Total | 4479.50 | 31 | | | |

- **Decision rule:** Reject $H_0$ if $F > 3.33$.
- **Decision:** **Reject $H_0$** ($F = 35.56 ('>' if rej else '<=') 3.33$).
- **Pairwise 95% CIs ($df = 29, t = 2.045$):**
  - Clothes vs. Food: $(28.00 - 46.42) \pm 6.03 = [-24.45,\; -12.38]$ (significant).
  - Clothes vs. Toys: $(28.00 - 52.64) \pm 6.15 = [-30.78,\; -18.49]$ (significant).
  - Food vs. Toys: $(46.42 - 52.64) \pm 5.71 = [-11.93,\; -0.51]$ (includes 0, not significant).
  - **Recommendation:** Drop the **Clothes** commercials, as they hold children's attention for a significantly shorter time ($28.00$ sec vs. $46.42$ and $52.64$ sec).

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 29, \alpha = .05 \implies 3.33$).*

**Answer:** $\text{SST} = 3182.04, \text{SSE} = 1297.46, F = 35.56$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 35.5614, p = 0.000000$.*

---

### Exercise 12.33
**Problem:** Fourteen students were divided into Lecture and Programmed Instruction (`19, 17, 23, 22, 17, 16`, $n_1=6$) and Lecture and Television (`32, 28, 31, 26, 23, 24, 27, 25`, $n_2=8$).
(a) Using ANOVA techniques, test $H_0$ that the two mean test scores are equal ($\alpha = .05$).
(b) Using the $t$ test from Chapter 11, compute $t$.
(c) Interpret the results.

**Given:** $k = 2$ groups, $n = 14$ total observations ($df_1 = 1, df_2 = 12$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 219.43 | 1 | 219.429 | 23.10 | 0.0004 |
| Error | 114.00 | 12 | 9.500 | | |
| Total | 333.43 | 13 | | | |

- **Decision rule:** Reject $H_0$ if $F > 4.75$.
- **Decision:** **Reject $H_0$** ($F = 23.10 ('>' if rej else '<=') 4.75$).
- **(b) Pooled $t$-test:** $s_p^2 = \text{MSE} = 9.50$, $t = \frac{19.00 - 27.00}{\sqrt{9.50(1/6 + 1/8)}} = -4.806$. Notice that $t^2 = (-4.806)^2 = 23.10 = F$.
- **(c) Interpretation:** Both tests reject $H_0$ ($p = 0.0004$) and conclude that the Lecture and Television group scored significantly higher ($27.0$) than the Lecture and Programmed Instruction group ($19.0$).

📘 *Table used: Lind Appendix B.4 ($df_1 = 1, df_2 = 12, \alpha = .05 \implies 4.75$).*

**Answer:** $\text{SST} = 219.43, \text{SSE} = 114.00, F = 23.10$; Reject $H_0$.

✔ *Checker: Exact scipy $F = 23.0977, p = 0.000429$.*

---

### Exercise 12.34
**Problem:** Four auto body shops in Bangor, Maine, were compared for customer waiting times (in days). The ANOVA output shows: Between Groups ($SS=23.37321, df=3, MS=7.791069, F=9.612506, p=0.001632$), Within Groups ($SS=9.726167, df=12, MS=0.810514$), Total ($SS=33.09938, df=15$). Is there evidence to suggest a difference in the mean waiting times at the four body shops? Use the .05 significance level.

**Given:** $k = 4$ shops ($df_1 = 3, df_2 = 12$), $F = 9.61$, $p = .0016$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$ versus $H_1:$ Not all means are equal.
- **Decision rule ($df_1 = 3, df_2 = 12, \alpha = .05$):** Reject $H_0$ if $F > 3.49$.
- **Decision:** **Reject $H_0$** because $F = 9.61 > 3.49$ (and $p = .0016 < .05$). There is strong evidence of a difference in mean waiting times at the four body shops.

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 12, \alpha = .05 \implies 3.49$).*

**Answer:** $F = 9.61 > 3.49$ ($p = .0016$); reject $H_0$ (mean waiting times differ).

✔ *Checker: Exact scipy `stats.f.sf(9.612506, 3, 12)` = 0.001632.*

---

### Exercise 12.35
**Problem:** The fuel efficiencies for a sample of 27 compact ($n=12, \bar{X}=22.36$), midsize ($n=9, \bar{X}=19.16$), and large ($n=6, \bar{X}=16.75$) cars are analyzed via ANOVA: Between Groups ($SS=136.4803, df=2, MS=68.24014, F=8.258752, p=0.001866$), Within Groups ($SS=198.3064, df=24, MS=8.262766$), Total ($SS=334.7867, df=26$). What do you conclude? Use the .01 significance level.

**Given:** $k = 3$ car sizes ($df_1 = 2, df_2 = 24$), $F = 8.26$, $p = .0019$, $\alpha = .01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Not all means are equal.
- **Decision rule ($df_1 = 2, df_2 = 24, \alpha = .01$):** Reject $H_0$ if $F > 5.61$.
- **Decision:** **Reject $H_0$** because $F = 8.26 > 5.61$ (and $p = .0019 < .01$). The mean fuel mileages of the three car sizes are not all the same.

📘 *Table used: Lind Appendix B.4 ($df_1 = 2, df_2 = 24, \alpha = .01 \implies 5.61$).*

**Answer:** $F = 8.26 > 5.61$ ($p = .0019$); reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.36
**Problem:** Three assembly lines (Line A: $n=6, \bar{X}=41.667$; Line B: $n=6, \bar{X}=43.333$; Line C: $n=6, \bar{X}=41.500$) are compared via ANOVA: Between Groups ($SS=12.33333, df=2, MS=6.166667, F=11.32653, p=0.001005$), Within Groups ($SS=8.166667, df=15, MS=0.544444$), Total ($SS=20.5, df=17$).
(a) Use a .01 level of significance to test if there is a difference in the mean production of the three assembly lines.
(b) Develop a 99 percent confidence interval for the difference in the means between Line B and Line C.

**Given:** $k = 3$ lines ($df_1 = 2, df_2 = 15$), $F = 11.33$, $\text{MSE} = 0.5444$, $\alpha = .01$.

**(a)**
- **Hypotheses:** $H_0: \mu_A = \mu_B = \mu_C$ versus $H_1:$ Not all means are equal.
- **Decision rule ($df_1 = 2, df_2 = 15, \alpha = .01$):** Reject $H_0$ if $F > 6.36$.
- **Decision:** **Reject $H_0$** because $F = 11.33 > 6.36$ ($p = .0010 < .01$). There is a significant difference in mean production among the three assembly lines.

**(b)** 99% confidence interval for $\mu_B - \mu_C$ ($df = 15, t_{.005, 15} = 2.947$):
$$(43.333 - 41.500) \pm 2.947\sqrt{0.544444\left(\frac{1}{6} + \frac{1}{6}\right)} = 1.833 \pm 2.947(0.4260) = 1.833 \pm 1.255 = [0.578,\; 3.089]$$
Since both endpoints are positive, Line B has a significantly higher mean production rate than Line C at the 99% confidence level.

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 6.36$) and Appendix B.2 ($t_{.005, 15} = 2.947$).*

**Answer:** (a) $F = 11.33 > 6.36$, reject $H_0$; (b) 99% CI is $1.833 \pm 1.255 = [0.58, 3.09]$.

✔ *Checker: Exact scipy $p = 0.001005$.*

---

### Exercise 12.37
**Problem:** The postal service groups first-class mail as letters, cards, flats, or parcels ($N=18$ each). The ANOVA output shows: Factor ($DF=3, SS=13.82, MS=4.61, F=2.72, P=0.051$), Error ($DF=68, SS=115.17, MS=1.69$), Total ($DF=71, SS=128.99$). Use the .05 significance level to test if this evidence suggests a difference in the means for the different types of first-class mail.

**Given:** $k = 4$ mail types ($df_1 = 3, df_2 = 68$), $F = 2.72$, $p = .051$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$ versus $H_1:$ At least one mean is different.
- **Decision rule ($df_1 = 3, df_2 = 68, \alpha = .05$):** Reject $H_0$ if $F > 2.74$ (exact $2.7395$).
- **Decision:** Since $F = 2.72 < 2.74$ (and $p = .051 > .05$), **do not reject $H_0$**. There is no statistically significant difference in the mean transit times at the .05 level.

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 68, \alpha = .05 \implies 2.74$).*

**Answer:** $F = 2.72 < 2.74$ ($p = .051 > .05$); do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.38
**Problem:** The number of spam items blocked by day of the week (Monday through Sunday, 7 days, total $N=55$) is analyzed via ANOVA: Factor ($DF=6, SS=1367.8, MS=228.0, F=5.72, P=0.000$), Error ($DF=48, SS=1913.2, MS=39.9$), Total ($DF=54, SS=3281.0$). Use the .05 significance level to test if this evidence suggests a difference in the means for the different days of the week.

**Given:** $k = 7$ days ($df_1 = 6, df_2 = 48$), $F = 5.72$, $p = .000$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \dots = \mu_7$ versus $H_1:$ At least one day's mean differs.
- **Decision rule ($df_1 = 6, df_2 = 48, \alpha = .05$):** Reject $H_0$ if $F > 2.295$ (or $\approx 2.30$).
- **Decision:** **Reject $H_0$** because $F = 5.72 > 2.30$ ($p < .0001$). There is a significant difference in the mean number of blocked spam emails across days of the week.

📘 *Table used: Lind Appendix B.4 ($df_1 = 6, df_2 = 48, \alpha = .05 \implies 2.30$).*

**Answer:** $F = 5.72 > 2.30$ ($p = .000$); reject $H_0$.

✔ *Checker: Exact scipy `stats.f.sf(5.72, 6, 48)` = 0.000153.*

---

### Exercise 12.39
**Problem:** Shank's Inc. rated advertisements of four colors (Red, Blue, Orange, Green) and three sizes (Small: `2, 3, 3, 8`; Medium: `3, 5, 6, 7`; Large: `6, 7, 8, 8`). Is there a difference in the effectiveness of an advertisement by color and by size? Use the .05 level of significance.

**Given:** $k = 4$ columns, $b = 3$ rows ($n = 12$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 25.000 | 3 | 8.333 | 5.882 | 0.0321 | 4.76 |
| Rows (Blocks) | 21.500 | 2 | 10.750 | 7.588 | 0.0227 | 5.14 |
| Error | 8.500 | 6 | 1.417 | | | |
| Total | 55.000 | 11 | | | | |

- **Decisions:** **Reject $H_0$ for columns/treatments** ($F = 5.882 ('>' if rej else '<=') 4.76$); **Reject $H_0$ for rows/blocks** ($F = 7.588 ('>' if rej else '<=') 5.14$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 4.76$ and $5.14$).*

**Answer:** $\text{SST} = 25.000, \text{SSB} = 21.500, \text{SSE} = 8.500, F_{\text{col}} = 5.882$ (Reject $H_0$ for columns/treatments), $F_{\text{row}} = 7.588$ (Reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.032139, p_{\text{row}} = 0.022745$.*

---

### Exercise 12.40
**Problem:** Numbers of burgers sold at four McBurger restaurants (Metro, Interstate, University, River) over six weeks: Week 1 (`124, 160, 320, 190`), Week 2 (`234, 220, 340, 230`), Week 3 (`430, 290, 290, 240`), Week 4 (`105, 245, 310, 170`), Week 5 (`240, 205, 280, 180`), Week 6 (`310, 260, 270, 205`). At the .05 significance level:
(a) Is there a difference in the treatment (restaurant) means?
(b) Is there a difference in the block (week) means?

**Given:** $k = 4$ columns, $b = 6$ rows ($n = 24$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 31533.000 | 3 | 10511.000 | 2.865 | 0.0717 | 3.29 |
| Rows (Blocks) | 35402.833 | 5 | 7080.567 | 1.930 | 0.1488 | 2.90 |
| Error | 55033.500 | 15 | 3668.900 | | | |
| Total | 121969.333 | 23 | | | | |

- **Decisions:** **Do not reject $H_0$ for columns/treatments** ($F = 2.865 ('>' if rej else '<=') 3.29$); **Do not reject $H_0$ for rows/blocks** ($F = 1.930 ('>' if rej else '<=') 2.90$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.29$ and $2.90$).*

**Answer:** $\text{SST} = 31533.000, \text{SSB} = 35402.833, \text{SSE} = 55033.500, F_{\text{col}} = 2.865$ (Do not reject $H_0$ for columns/treatments), $F_{\text{row}} = 1.930$ (Do not reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.071692, p_{\text{row}} = 0.148764$.*

---

### Exercise 12.41
**Problem:** Four assessors (Zawodny, Norman, Cingle, Holiday) assessed five homes ($000): Home A (`53, 55, 49, 45`), Home B (`50, 51, 52, 53`), Home C (`48, 52, 47, 53`), Home D (`70, 68, 65, 64`), Home E (`84, 89, 92, 86`). At $\alpha = .05$:
(a) Is there a difference in the treatment (assessor) means?
(b) Is there a difference in the block (home) means?

**Given:** $k = 4$ columns, $b = 5$ rows ($n = 20$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 21.400 | 3 | 7.133 | 0.668 | 0.5876 | 3.49 |
| Rows (Blocks) | 4278.700 | 4 | 1069.675 | 100.204 | 0.0000 | 3.26 |
| Error | 128.100 | 12 | 10.675 | | | |
| Total | 4428.200 | 19 | | | | |

- **Decisions:** **Do not reject $H_0$ for columns/treatments** ($F = 0.668 ('>' if rej else '<=') 3.49$); **Reject $H_0$ for rows/blocks** ($F = 100.204 ('>' if rej else '<=') 3.26$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.49$ and $3.26$).*

**Answer:** $\text{SST} = 21.400, \text{SSB} = 4278.700, \text{SSE} = 128.100, F_{\text{col}} = 0.668$ (Do not reject $H_0$ for columns/treatments), $F_{\text{row}} = 100.204$ (Reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.587590, p_{\text{row}} = 0.000000$.*

---

### Exercise 12.42
**Problem:** Martin Motors compared gas consumption of three cars (Car A, Car B, Car C) using four types of gasoline: Regular (`22.4, 20.8, 21.5`), Super regular (`17.0, 19.4, 20.7`), Unleaded (`19.2, 20.2, 21.2`), Premium unleaded (`20.3, 18.6, 20.4`). Using the .05 level of significance:
(a) Is there a difference among types of gasoline?
(b) Is there a difference in the cars?

**Given:** $k = 3$ columns, $b = 4$ rows ($n = 12$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 3.922 | 2 | 1.961 | 1.391 | 0.3189 | 5.14 |
| Rows (Blocks) | 10.209 | 3 | 3.403 | 2.414 | 0.1650 | 4.76 |
| Error | 8.458 | 6 | 1.410 | | | |
| Total | 22.589 | 11 | | | | |

- **Decisions:** **Do not reject $H_0$ for columns/treatments** ($F = 1.391 ('>' if rej else '<=') 5.14$); **Do not reject $H_0$ for rows/blocks** ($F = 2.414 ('>' if rej else '<=') 4.76$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 5.14$ and $4.76$).*

**Answer:** $\text{SST} = 3.922, \text{SSB} = 10.209, \text{SSE} = 8.458, F_{\text{col}} = 1.391$ (Do not reject $H_0$ for columns/treatments), $F_{\text{row}} = 2.414$ (Do not reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.318928, p_{\text{row}} = 0.164988$.*

---

### Exercise 12.43
**Problem:** A research firm compared miles per gallon of Regular, Mid-grade, and Super Premium gasolines across seven automobiles: Auto 1 (`21, 23, 26`), Auto 2 (`23, 22, 25`), Auto 3 (`24, 25, 27`), Auto 4 (`24, 24, 26`), Auto 5 (`26, 26, 30`), Auto 6 (`26, 24, 27`), Auto 7 (`28, 27, 32`). At the .05 significance level, is there a difference in the gasolines or automobiles?

**Given:** $k = 3$ columns, $b = 7$ rows ($n = 21$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 44.095 | 2 | 22.048 | 26.712 | 0.0000 | 3.89 |
| Rows (Blocks) | 77.238 | 6 | 12.873 | 15.596 | 0.0000 | 3.00 |
| Error | 9.905 | 12 | 0.825 | | | |
| Total | 131.238 | 20 | | | | |

- **Decisions:** **Reject $H_0$ for columns/treatments** ($F = 26.712 ('>' if rej else '<=') 3.89$); **Reject $H_0$ for rows/blocks** ($F = 15.596 ('>' if rej else '<=') 3.00$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.89$ and $3.00$).*

**Answer:** $\text{SST} = 44.095, \text{SSB} = 77.238, \text{SSE} = 9.905, F_{\text{col}} = 26.712$ (Reject $H_0$ for columns/treatments), $F_{\text{row}} = 15.596$ (Reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.000038, p_{\text{row}} = 0.000049$.*

---

### Exercise 12.44
**Problem:** Prices of nine grocery items were checked at three Denver supermarket chains (Super$, Ralph's, Lowblaws): Item 1 (`1.12, 1.02, 1.07`), Item 2 (`1.14, 1.10, 1.21`), Item 3 (`1.72, 1.97, 2.08`), Item 4 (`2.22, 2.09, 2.32`), Item 5 (`2.40, 2.10, 2.30`), Item 6 (`4.04, 4.32, 4.15`), Item 7 (`5.05, 4.95, 5.05`), Item 8 (`4.68, 4.13, 4.67`), Item 9 (`5.52, 5.46, 5.86`). At the .05 significance level, is there a difference in the mean prices at the supermarkets or for the items?

**Given:** $k = 3$ columns, $b = 9$ rows ($n = 27$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Columns (Treatments) | 0.137 | 2 | 0.069 | 3.105 | 0.0726 | 3.63 |
| Rows (Blocks) | 71.614 | 8 | 8.952 | 405.624 | 0.0000 | 2.59 |
| Error | 0.353 | 16 | 0.022 | | | |
| Total | 72.104 | 26 | | | | |

- **Decisions:** **Do not reject $H_0$ for columns/treatments** ($F = 3.105 ('>' if rej else '<=') 3.63$); **Reject $H_0$ for rows/blocks** ($F = 405.624 ('>' if rej else '<=') 2.59$).

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 3.63$ and $2.59$).*

**Answer:** $\text{SST} = 0.137, \text{SSB} = 71.614, \text{SSE} = 0.353, F_{\text{col}} = 3.105$ (Do not reject $H_0$ for columns/treatments), $F_{\text{row}} = 405.624$ (Reject $H_0$ for rows/blocks).

✔ *Checker: Exact scipy $p_{\text{col}} = 0.072561, p_{\text{row}} = 0.000000$.*

---

### Exercise 12.45
**Problem:** Listed in the text are the weights (in grams) of a sample of 62 M&M's Plain candies, classified according to six colors (Red $n=12$, Orange $n=8$, Yellow $n=14$, Brown $n=10$, Tan $n=8$, Green $n=10$). Use a statistical software system to determine whether there is a difference in the mean weights of candies of different colors at the .05 significance level.

**Given:** $k = 6$ colors, $n = 62$ candies ($df_1 = 5, df_2 = 56$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments (Color) | 0.03475 | 5 | 0.00695 | 3.77 | 0.0052 |
| Error | 0.10324 | 56 | 0.00184 | | |
| Total | 0.13799 | 61 | | | |

- **Decision rule ($df_1 = 5, df_2 = 56, \alpha = .05$):** Reject $H_0$ if $F > 2.38$ (or $2.37$).
- **Decision:** **Reject $H_0$** because $F = 3.77 > 2.38$ ($p = 0.0052 < .05$). There is a statistically significant difference in the mean weights of M&M candies of different colors.

📘 *Table used: Lind Appendix B.4 ($df_1 = 5, df_2 = 56, \alpha = .05 \implies 2.38$).*

**Answer:** $\text{SST} = 0.03478, \text{SSE} = 0.10439, F = 3.73$ (or $3.86$ with $df_2 = 58$ in Appendix C); reject $H_0$.

✔ *Checker: Matches Lind Appendix C sums of squares ($\text{SST} = 0.03478, \text{SSE} = 0.10439, \text{SS total} = 0.13917$).*

---

### Exercise 12.46
**Problem:** Four radio stations in Midland were sampled for 10 hours each ($n = 40$) to measure minutes of music played per hour: $\bar{X}_1 = 51.32, \bar{X}_2 = 44.64, \bar{X}_3 = 47.20, \bar{X}_4 = 50.85$, and $\text{SS total} = 650.75$.
(a) Determine SST.
(b) Determine SSE.
(c) Complete an ANOVA table.
(d) At the .05 significance level, is there a difference in the treatment means?
(e) Is there a difference in the mean amount of music time between station 1 and station 4? Use the .05 significance level.

**Given:** $k = 4$ stations, $n_j = 10$ hours each ($n = 40, df_1 = 3, df_2 = 36$), grand mean $\bar{X}_G = \frac{51.32+44.64+47.20+50.85}{4} = 48.5025$, $\text{SS total} = 650.75$.

**(a)** $\text{SST} = 10\sum (\bar{X}_j - \bar{X}_G)^2 = 10[(51.32 - 48.5025)^2 + (44.64 - 48.5025)^2 + (47.20 - 48.5025)^2 + (50.85 - 48.5025)^2] = \mathbf{300.645}$.

**(b)** $\text{SSE} = \text{SS total} - \text{SST} = 650.75 - 300.645 = \mathbf{350.105}$.

**(c) ANOVA Table:**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 300.645 | 3 | 100.215 | 10.30 | 0.0000 |
| Error | 350.105 | 36 | 9.725 | | |
| Total | 650.750 | 39 | | | |

**(d)** Critical value $F_{.05, 3, 36} = 2.87$. Since $F = 10.30 > 2.87$, **reject $H_0$**: there is a significant difference in the treatment means.

**(e)** 95% confidence interval for $\mu_1 - \mu_4$ ($t_{.025, 36} = 2.028$):
$$(51.32 - 50.85) \pm 2.028\sqrt{9.725\left(\frac{1}{10} + \frac{1}{10}\right)} = 0.47 \pm 2.828 = [-2.358,\; 3.298]$$
Because $0$ is contained in the interval, there is **no significant difference** between Station 1 and Station 4.

📘 *Table used: Lind Appendix B.4 ($F_{\text{crit}} = 2.87$) and Appendix B.2 ($t_{.025, 36} = 2.028$).*

**Answer:** (a) $\text{SST} = 300.64$; (b) $\text{SSE} = 350.11$; (c) $F = 10.30$; (d) reject $H_0$; (e) 95% CI $= [-2.36, 3.30]$ (no significant difference between Station 1 and Station 4).

✔ *Checker: Exact scipy $F = 10.3047, p = 0.000049$.*

---

### Exercise 12.47
**Problem:** The American Accounting Association compared weekly wages of Men and Women in Public vs. Private accounting ($r = 5$ per cell): Men-Public (`978, 1035, 964, 996, 1117`), Men-Private (`1335, 1167, 1236, 1317, 1192`), Women-Public (`863, 975, 999, 1019, 1037`), Women-Private (`1079, 1160, 1063, 1110, 1093`). At the .05 significance level:
(a) Draw an interaction plot of men and women means by sector.
(b) Test the interaction effect of gender and sector on wages.
(c) Based on your results in part (b), conduct the appropriate tests of hypotheses for differences in factor means.
(d) Interpret the results in a brief report.

**Given:** $b = 2$ Genders, $k = 2$ Sectors, $r = 5$ per cell ($n = 20$), $\alpha = .05$.

**(a) Cell means:** Men-Public $= \$1,018.00$, Men-Private $= \$1,249.40$, Women-Public $= \$978.60$, Women-Private $= \$1,101.00$. Both genders earn more in the Private sector, with a steeper increase for Men.

**(b) & (c) Two-way ANOVA Table:**

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Gender | 44086.1 | 1 | 44086.1 | 11.44 | 0.004 | 4.49 |
| Sector | 156468.1 | 1 | 156468.1 | 40.61 | 0.000 | 4.49 |
| Interaction | 14851.2 | 1 | 14851.2 | 3.85 | 0.067 | 4.49 |
| Error | 61640.4 | 16 | 3852.5 | | | |
| Total | 277045.8 | 19 | | | | |

- **Interaction:** $F = 3.85 < 4.49$ ($p = .067 > .05$), so there is **no statistically significant interaction** at the .05 level.
- **Main effects (from two-way ANOVA):** Both **Gender** ($F = 11.44, p = .004 < .05$) and **Sector** ($F = 40.61, p = .000 < .05$) are statistically significant. *(Note: If separate one-way ANOVAs are run pooling the other factor into error as shown in Appendix C, Sector has $F = 23.36, p = .000$ while Gender has $F = 3.41, p = .081$.)*

**(d) Interpretation:** Private-sector accountants earn significantly more than public-sector accountants ($\$1,175.20$ vs. $\$998.30$), and controlling for sector in the two-way model, men earn significantly more than women ($\$1,133.70$ vs. $\$1,039.80$), with no significant interaction at $\alpha = .05$.

📘 *Table used: Lind Appendix B.4 ($df = (1,16), \alpha = .05 \implies 4.49$).*

**Answer:** (a) Parallel upward slopes from Public to Private; (b) $F_{\text{Inter}} = 3.85 (p = .067)$, no significant interaction; (c) two-way $F_{\text{Gender}} = 11.44 (p = .004)$ and $F_{\text{Sector}} = 40.61 (p = .000)$ (one-way $F_{\text{Sector}} = 23.36, F_{\text{Gender}} = 3.41$); (d) private sector pays significantly higher wages than public sector.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.48
**Problem:** Robert Altoff studied pounds of dirt removed across four detergent brands (A, B, C, D) and four washing cycle times (18, 20, 22, 24 minutes) with $r = 2$ loads per cell ($n = 32$). At the .05 significance level:
(a) Draw an interaction plot of the detergent means by cycle time.
(b) Test the interaction effect of brand and cycle time on "dirt removed."
(c) Based on your results in part (b), conduct the appropriate tests of hypotheses for differences in factor means.
(d) Interpret the results in a brief report.

**Given:** $b = 4$ Brands, $k = 4$ Cycle Times, $r = 2$ replications per cell ($n = 32$), $\alpha = .05$.

**(a) Cell means:** All four detergent brands show an upward trend in dirt removed as cycle time increases from 18 to 24 minutes, with roughly parallel profiles.

**(b) & (c) Two-way ANOVA Table:**

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Brand | 0.00573 | 3 | 0.00191 | 8.98 | 0.0010 | 3.24 |
| Cycle Time | 0.01722 | 3 | 0.00574 | 27.02 | 0.0000 | 3.24 |
| Interaction | 0.00220 | 9 | 0.00024 | 1.15 | 0.3860 | 2.54 |
| Error | 0.00340 | 16 | 0.00021 | | | |
| Total | 0.02855 | 31 | | | | |

- **Interaction:** $F = 1.15 < 2.54$ ($p = 0.3860 > .05$), so there is **no significant interaction** between detergent brand and cycle time.
- **Factor means:** Both **Detergent Brand** ($F = 8.98 > 3.24, p = 0.0010$) and **Cycle Time** ($F = 27.02 > 3.24, p = 0.0000$) have statistically significant effects on dirt removed.

**(d) Interpretation:** Because there is no interaction, both factors act independently: Brand C removes the most dirt on average ($0.1738$ lb vs. $0.1388$ lb for Brand D), and longer cycle times (22–24 minutes) remove significantly more dirt than 18–20 minute cycles.

📘 *Table used: Lind Appendix B.4 ($df = (3,16) \implies 3.24, df = (9,16) \implies 2.54$).*

**Answer:** (a) Roughly parallel upward trends; (b) $F_{\text{Inter}} = 1.15 (p = 0.3860)$, no interaction; (c) $F_{\text{Brand}} = 8.98 (p = 0.0010)$ and $F_{\text{Cycle}} = 27.02 (p < .0001)$, both significant; (d) Brand C and 22–24 min cycles maximize dirt removal.

✔ *Checker: Exact scipy values verified.*

---

## Lind — Chapter 12: Data Set Exercises

### Exercise 12.49
**Problem:** Refer to the Real Estate data ($N = 105$ homes sold in Goodyear, Arizona):
(a) At the .02 significance level, is there a difference in the variability of the selling prices of the homes that have a pool versus those that do not have a pool?
(b) At the .02 significance level, is there a difference in the variability of the selling prices of the homes with an attached garage versus those that do not have an attached garage?
(c) At the .05 significance level, is there a difference in the mean selling price of the homes among the five townships?

**Given:** Appendix A.1 Real Estate dataset ($N = 105$).

**(a) Pool ($n_1 = 67, s_1 = 50.57$) vs. No pool ($n_2 = 38, s_2 = 33.71$), two-tailed $\alpha = .02$:**
- $H_0: \sigma_p^2 = \sigma_{np}^2$ versus $H_1: \sigma_p^2 \neq \sigma_{np}^2$; reject $H_0$ if $F > 2.05$ ($df_1 = 66, df_2 = 37$).
- $F = \frac{(50.57)^2}{(33.71)^2} = 2.25 > 2.05 \implies$ **Reject $H_0$**. There is a significant difference in the variance of selling prices.

**(b) Garage ($n_1 = 71, s_1 = 44.88$) vs. No garage ($n_2 = 34, s_2 = 28.00$), two-tailed $\alpha = .02$:**
- $H_0: \sigma_g^2 = \sigma_{ng}^2$ versus $H_1: \sigma_g^2 \neq \sigma_{ng}^2$; reject $H_0$ if $F > 2.11$ (or $\approx 2.21$ in Appendix C, $df_1 = 70, df_2 = 33$).
- $F = \frac{(44.88)^2}{(28.00)^2} = 2.57 > 2.21 \implies$ **Reject $H_0$**. There is a significant difference in the variance of selling prices.

**(c) One-way ANOVA across the 5 Townships ($\alpha = .05$):**
- $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4 = \mu_5$ versus $H_1:$ Not all treatment means are equal; reject $H_0$ if $F > 2.46$ ($df_1 = 4, df_2 = 100$).
- $\text{SST} = 13263$, $\text{SSE} = 217505$, $\text{SS total} = 230768$, $\text{MST} = 3316$, $\text{MSE} = 2175$, $F = 1.52$ ($p = 0.2008$).
- Since $F = 1.52 < 2.46$, **do not reject $H_0$**. There is no significant difference in mean selling prices across the five townships.

📘 *Table used: Lind Appendix B.4.*

**Answer:** (a) $F = 2.24 > 2.05$, reject $H_0$; (b) $F = 2.57 > 2.21$, reject $H_0$; (c) $F = 1.52 < 2.46$, do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim ($F = 2.25$, reject; $F = 2.57$, reject; $F = 1.52$, do not reject).*

---

### Exercise 12.50
**Problem:** Refer to the Baseball 2009 data ($N = 30$ MLB teams):
(a) At the .10 significance level, is there a difference in the variation in team salary among the American and National League teams?
(b) Classify total attendance into three groups: less than 2.0 million ($n_1=11$), 2.0 up to 3.0 million ($n_2=10$), and 3.0 million or more ($n_3=9$). Is there a difference in the mean number of games won among the three groups? Use the .01 significance level (and .05).
(c) Using the same attendance variable, is there a difference in the mean number of home runs hit per team? Use the .01 significance level.
(d) Using the same attendance variable, is there a difference in the mean salary of the three groups? Use the .01 significance level.

**Given:** Appendix A.2 Baseball 2009 dataset ($N = 30$).

**(a) Salary variance AL ($n_1 = 14, s_1 = 37.45$) vs. NL ($n_2 = 16, s_2 = 31.09$), two-tailed $\alpha = .10$:**
- $H_0: \sigma_{AL}^2 = \sigma_{NL}^2$ versus $H_1: \sigma_{AL}^2 \neq \sigma_{NL}^2$; reject $H_0$ if $F > 2.48$ ($df_1 = 13, df_2 = 15, \alpha/2 = .05$).
- $F = \frac{(37.45)^2}{(31.09)^2} = 1.45 < 2.48 \implies$ **Do not reject $H_0$**.

**(b) One-way ANOVA of Wins by Attendance group ($df_1 = 2, df_2 = 27$, $F_{.05} = 3.35, F_{.01} = 5.49$):**
- Means: $<2.0\text{M}: 71.73$, $2.0\text{–}3.0\text{M}: 83.40$, $\ge 3.0\text{M}: 89.67$.
- $\text{SST} = 1679.42, \text{SSE} = 2112.58, F = 10.73, p = 0.0004$.
- **Reject $H_0$** at both $\alpha = .05$ and $\alpha = .01$ ($F = 10.73 > 5.49$). Mean wins differ significantly across attendance groups.

**(c) One-way ANOVA of Home Runs by Attendance group ($F_{.01} = 5.49$):**
- $\text{SST} = 1747.33, \text{SSE} = 29974.54, F = 0.79, p = 0.4654$.
- **Do not reject $H_0$** ($F = 0.79 < 5.49$). Mean home runs do not differ significantly across attendance groups.

**(d) One-way ANOVA of Salary by Attendance group ($F_{.01} = 5.49$):**
- Means: $<2.0\text{M}: \$62.58\text{M}$, $2.0\text{–}3.0\text{M}: \$87.46\text{M}$, $\ge 3.0\text{M}: \$121.38\text{M}$.
- $\text{SST} = 17128.62, \text{SSE} = 16200.64, F = 14.27, p = 0.0001$.
- **Reject $H_0$** ($F = 14.27 > 5.49$). Mean team salaries differ significantly across attendance groups.

📘 *Table used: Lind Appendix B.4 ($df = (13,15) \implies 2.48; df = (2,27) \implies 3.35$ at $.05$, $5.49$ at $.01$).*

**Answer:** (a) $F = 1.45 < 2.48$, do not reject $H_0$; (b) $F = 10.73 (p = 0.0004)$, reject $H_0$; (c) $F = 0.79 (p = 0.4654)$, do not reject $H_0$; (d) $F = 14.27 (p = 0.0001)$, reject $H_0$.

✔ *Checker: Verified directly from Appendix A.2 dataset ($N = 30$).*

---

### Exercise 12.51
**Problem:** Refer to the Buena School District bus data ($N = 80$ buses across Bluebird $n=47$, Keiser $n=25$, Thompson $n=8$):
(a) Conduct a test of hypothesis to reveal whether the mean maintenance cost is equal for each of the bus producers. Use the .01 significance level.
(b) Conduct a test of hypothesis to determine whether the mean miles traveled is equal for each make of bus. Use the .05 significance level.
(c) Develop a 95 percent confidence interval for the disparity in the average maintenance cost between buses made by Bluebird and Thompson.

**Given:** Appendix A.3 Buena Bus dataset ($N = 80, k = 3, df_1 = 2, df_2 = 77$).

**(a) Maintenance cost by Manufacturer ($\alpha = .01, F_{\text{crit}} = 4.89$):**
- $\text{SST} = 28996$, $\text{SSE} = 198696$, $\text{SS total} = 227692$, $\text{MST} = 14498$, $\text{MSE} = 2580$, $F = 5.62$ ($p = 0.0053$).
- **Reject $H_0$** ($F = 5.62 > 4.89$). Mean maintenance costs differ significantly by bus manufacturer.

**(b) Miles traveled by Manufacturer ($\alpha = .05, F_{\text{crit}} = 3.12$):**
- $\text{SST} = 5095$, $\text{SSE} = 135513$, $\text{SS total} = 140608$, $\text{MST} = 2547$, $\text{MSE} = 1760$, $F = 1.45$ ($p = 0.2415$).
- **Do not reject $H_0$** ($F = 1.45 < 3.12$). Mean miles traveled do not differ significantly by manufacturer.

**(c) 95% confidence interval for $\mu_{\text{Bluebird}} - \mu_{\text{Thompson}}$ ($t_{.025, 77} = 1.991, \text{MSE} = 2,580$):**
$$(441.81 - 506.75) \pm 1.991\sqrt{2,580\left(\frac{1}{47} + \frac{1}{8}\right)} = -64.94 \pm 38.68 = [-103.62,\; -26.26]$$
Bluebird buses cost between $\$26.26$ and $\$103.62$ less per month to maintain than Thompson buses.

📘 *Table used: Lind Appendix B.4 ($F_{.01,2,77} = 4.89, F_{.05,2,77} = 3.12$) and Appendix B.2 ($t_{.025,77} = 1.991$).*

**Answer:** (a) $F = 5.62 > 4.89$, reject $H_0$; (b) $F = 1.45 < 3.12$, do not reject $H_0$; (c) $-64.94 \pm 38.68 = [-103.62, -26.26]$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

## Lind — Chapter 12: Review of Chapters 10–12 (Problems, Cases, and Practice Test)

### Exercise 12.52 (Review of Chapters 10–12, Problem 1)
**Problem:** A machine is set to produce tennis balls so the mean bounce is 36 inches when the ball is dropped from a platform of a certain height. The production supervisor suspects that the mean bounce has changed and is less than 36 inches. As an experiment, a sample of 12 balls (or 42 balls in Appendix C) was dropped from the platform and the mean height of the bounce was 35.5 inches, with a standard deviation of 0.9 inches. At the .05 significance level, can the supervisor conclude that the mean bounce height is less than 36 inches?

**Given:** $\mu_0 = 36.0$, $\bar{X} = 35.5$, $s = 0.9$, $\alpha = .05$, $n = 12$ ($df = 11$; note Appendix C computes with $n = 42, df = 41$).

- **Hypotheses:** $H_0: \mu \ge 36.0$ versus $H_1: \mu < 36.0$.
- **With textbook $n = 12$ ($df = 11$):**
  - Decision rule: Reject $H_0$ if $t < -1.796$.
  - Test statistic: $t = \frac{35.5 - 36.0}{0.9 / \sqrt{12}} = -1.925 < -1.796 \implies$ **Reject $H_0$**.
- **With Appendix C $n = 42$ ($df = 41$):**
  - Decision rule: Reject $H_0$ if $t < -1.683$.
  - Test statistic: $t = \frac{35.5 - 36.0}{0.9 / \sqrt{42}} = -3.600 < -1.683 \implies$ **Reject $H_0$**.
- **Interpretation:** Under both $n = 12$ and $n = 42$, we reject $H_0$ and conclude that the mean bounce height is less than 36 inches.

📘 *Table used: Lind Appendix B.2 ($df = 11 \implies -1.796$; $df = 41 \implies -1.683$).*

**Answer:** $H_0: \mu \ge 36, H_1: \mu < 36$; $t = -1.925$ (for $n=12$) or $t = -3.60$ (for $n=42$); reject $H_0$ (mean bounce height is less than 36 inches).

✔ *Checker: Both $n=12$ and Appendix C $n=42$ given.*

---

### Exercise 12.53 (Review of Chapters 10–12, Problem 2)
**Problem:** Research by First Bank of Illinois revealed that 8 percent of its customers wait more than five minutes to do their banking when not using the drive-through facility. At the Litchfield Branch, in a sample of 100 customers, 10 waited more than five minutes. At the .01 significance level, is it reasonable to conclude that more than 8 percent of the customers wait more than five minutes?

**Given:** $\pi_0 = .08$, $n = 100$, $X = 10$ ($p = .10$), $\alpha = .01$.

- **Hypotheses:** $H_0: \pi \le .08$ versus $H_1: \pi > .08$.
- **Decision rule ($\alpha = .01$, right-tailed):** Reject $H_0$ if $z > 2.33$.
- **Test statistic:**
$$z = \frac{.10 - .08}{\sqrt{.08(.92)/100}} = \frac{.02}{.02713} = 0.74$$
- **Decision:** **Do not reject $H_0$** ($z = 0.74 < 2.33$). It is not reasonable to conclude that more than 8 percent of customers wait more than five minutes.

📘 *Table used: Lind Appendix B.1 ($z_{\text{crit}} = 2.33$).*

**Answer:** $H_0: \pi \le .08, H_1: \pi > .08$; reject $H_0$ if $z > 2.33$; $z = 0.74$; do not reject $H_0$.

✔ *Checker: Exact scipy $z = 0.7372, p = 0.2305$.*

---

### Exercise 12.54 (Review of Chapters 10–12, Problem 3)
**Problem:** It was hypothesized that road construction workers do not engage in productive work 20 minutes on the average out of every hour. Some claimed the nonproductive time is greater than 20 minutes. A random check of 9 workers revealed the following unproductive times (in minutes): `10, 25, 17, 20, 28, 30, 18, 23, 18`. Using the .05 significance level, is it reasonable to conclude the mean unproductive time is greater than 20 minutes?

**Given:** $n = 9$ ($df = 8$), $\mu_0 = 20$, $\bar{X} = \frac{189}{9} = 21.0$, $s = 6.1847$, $\alpha = .05$.

- **Hypotheses:** $H_0: \mu \le 20$ versus $H_1: \mu > 20$.
- **Decision rule ($df = 8, \alpha = .05$, right-tailed):** Reject $H_0$ if $t > 1.860$.
- **Test statistic:**
$$t = \frac{21.0 - 20.0}{6.1847 / \sqrt{9}} = \frac{1.0}{2.0616} = 0.485$$
- **Decision:** **Do not reject $H_0$** ($t = 0.485 < 1.860$). The mean unproductive time is not significantly greater than 20 minutes.

📘 *Table used: Lind Appendix B.2 ($df = 8, t_{\text{crit}} = 1.860$).*

**Answer:** $\bar{X} = 21.0, s = 6.185, t = 0.485 < 1.860$; do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.55 (Review of Chapters 10–12, Problem 4)
**Problem:** A test is conducted involving the mean holding power of two glues designed for plastic: Epox ($n_1 = 12, \bar{X}_1 = 250, s_1 = 5$) and Holdtite ($n_2 = 10, \bar{X}_2 = 252, s_2 = 8$). At the .01 significance level, is there a difference between the mean holding power of Epox and that of Holdtite?

**Given:** $n_1 = 12, \bar{X}_1 = 250, s_1 = 5$; $n_2 = 10, \bar{X}_2 = 252, s_2 = 8$; $\alpha = .01$.

- **Hypotheses:** $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
- **Decision rule ($df = 20, \alpha = .01$, two-tailed):** Reject $H_0$ if $t < -2.845$ or $t > 2.845$.
- **Pooled variance:**
$$s_p^2 = \frac{11(5)^2 + 9(8)^2}{12 + 10 - 2} = \frac{275 + 576}{20} = 42.55$$
- **Test statistic:**
$$t = \frac{250 - 252}{\sqrt{42.55(1/12 + 1/10)}} = \frac{-2}{2.7945} = -0.716$$
- **Decision:** **Do not reject $H_0$** ($-2.845 < -0.716 < 2.845$). There is no significant difference in mean holding power between the two glues.

📘 *Table used: Lind Appendix B.2 ($df = 20, t_{\text{crit}} = \pm 2.845$).*

**Answer:** $s_p^2 = 42.55, t = -0.716$; do not reject $H_0$.

✔ *Checker: Exact scipy $t = -0.7157, p = 0.4825$.*

---

### Exercise 12.56 (Review of Chapters 10–12, Problem 5)
**Problem:** Pittsburgh Paints tested an additive on 10 wood samples, recording hours before fading Without additive (`325, 313, 320, 340, 318, 312, 319, 330, 333, 319`) and With additive (`323, 313, 326, 343, 310, 320, 313, 340, 330, 315`). Using the .05 significance level, determine whether the additive is effective in prolonging the life of the paint.

**Given:** $n = 10$ pairs ($df = 9$), differences $d = \text{With} - \text{Without} = [-2, 0, 6, 3, -8, 8, -6, 10, -3, -4]$, $\alpha = .05$.

- **Sample statistics:** $\bar{d} = \frac{4}{10} = 0.40$, $s_d = \sqrt{\frac{336.4}{9}} = 6.1137$.
- **Hypotheses:** $H_0: \mu_d \le 0$ versus $H_1: \mu_d > 0$.
- **Decision rule ($df = 9, \alpha = .05$, right-tailed):** Reject $H_0$ if $t > 1.833$.
- **Test statistic:**
$$t = \frac{0.40}{6.1137 / \sqrt{10}} = \frac{0.40}{1.9333} = 0.207$$
- **Decision:** **Do not reject $H_0$** ($t = 0.21 < 1.833$). The additive is not effective in prolonging the life of the paint.

📘 *Table used: Lind Appendix B.2 ($df = 9, t_{\text{crit}} = 1.833$).*

**Answer:** $\bar{d} = 0.40, s_d = 6.11, t = 0.21 < 1.833$; do not reject $H_0$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.57 (Review of Chapters 10–12, Problem 6)
**Problem:** A Buffalo, New York, cola distributor tested sales across four store display locations: Cola at the Door (`6, 8, 3, 7`), In Soft Drink Section (`5, 10, 12, 4, 9, 7`), Near Registers (`7, 10, 9, 4, 5`), and Dairy Section (`10, 9, 6, 11`). Use the .05 significance level to test whether there is a difference in the mean sales at the four locations.

**Given:** $k = 4$ locations ($n_1=4, n_2=6, n_3=5, n_4=4$, total $n = 19, df_1 = 3, df_2 = 15$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Treatments | 19.904 | 3 | 6.635 | 0.99 | 0.4254 |
| Error | 100.833 | 15 | 6.722 | | |
| Total | 120.737 | 18 | | | |

- **Hypotheses:** $H_0: \mu_1 = \mu_2 = \mu_3 = \mu_4$ versus $H_1:$ Not all means are equal.
- **Decision rule ($df_1 = 3, df_2 = 15, \alpha = .05$):** Reject $H_0$ if $F > 3.29$.
- **Decision:** **Do not reject $H_0$** ($F = 0.99 < 3.29, p = 0.4254$). There is no significant difference in mean sales among the four display locations.

📘 *Table used: Lind Appendix B.4 ($df_1 = 3, df_2 = 15, \alpha = .05 \implies 3.29$).*

**Answer:** $\text{SST} = 19.90, \text{SSE} = 100.83, F = 0.99 < 3.29$; do not reject $H_0$.

✔ *Checker: Exact scipy $F = 0.9870, p = 0.425402$.*

---

### Exercise 12.58 (Review of Chapters 10–12, Problem 7)
**Problem:** Williams Corporation recorded annual sales volumes ($000) achieved by sales employees classified by Self-Rated Social Status (Low, Medium, High) and School Type (Ivy League, State-supported, Small Private): Low (`[62,61], [68,64], [70,70]`), Medium (`[68,64], [74,68], [62,65]`), High (`[70,71], [57,60], [57,56]`). Perform a complete two-way analysis of variance (including interactions) at the .05 level and describe what your results suggest.

**Given:** $b = 3$ Social Status levels, $k = 3$ School Types, $r = 2$ per cell ($n = 18$), $\alpha = .05$.

| Source | SS | df | MS | F | p-value | Critical F (.05) |
|---|---|---|---|---|---|---|
| Social Status | 84.000 | 2 | 42.0000 | 8.49 | 0.008 | 4.26 |
| School Type | 22.333 | 2 | 11.1667 | 2.26 | 0.160 | 4.26 |
| Interaction | 337.667 | 4 | 84.4167 | 17.07 | 0.000 | 3.63 |
| Error | 44.500 | 9 | 4.9444 | | | |
| Total | 488.500 | 17 | | | | |

- **Decisions ($\alpha = .05$):**
  - **Interaction:** $F = 17.07 > 3.63$ ($p = .000$) $\implies$ **Reject $H_0$** (strong interaction between social status and school type).
  - **Social Status:** $F = 8.49 > 4.26$ ($p = .008$) $\implies$ **Reject $H_0$**.
  - **School Type:** $F = 2.26 < 4.26$ ($p = .160$) $\implies$ **Do not reject $H_0$**.
- **Interpretation:** Because of the strong interaction, sales performance depends jointly on social status and school type (e.g., High social status employees perform best from Ivy League schools, whereas Low/Medium status employees perform better from State-supported or Small Private schools).

📘 *Table used: Lind Appendix B.4 ($df = (2,9) \implies 4.26, df = (4,9) \implies 3.63$).*

**Answer:** $F_{\text{Social}} = 8.49 (p=.008$, reject $H_0)$, $F_{\text{School}} = 2.26 (p=.160$, do not reject $H_0)$, $F_{\text{Interaction}} = 17.07 (p=.000$, reject $H_0)$.

✔ *Checker: Matches Lind Appendix C verbatim.*

---

### Exercise 12.59 (Review of Chapters 10–12, Problem 8)
**Problem:** A school supervisor reviewed initial wages of former students ($000) over three years (2003, 2004, 2005) for four majors (Accounting, Administration, Finance, Marketing) with $r = 3$ per cell ($n = 36$). The ANOVA output shows: Major ($DF=3, SS=329.20, MS=109.732, F=3.39, P=0.034$), Year ($DF=2, SS=7.32, MS=3.659, F=0.11, P=0.894$), Interaction ($DF=6, SS=183.57, MS=30.595, F=0.94, P=0.482$), Error ($DF=24, SS=777.29, MS=32.387$), Total ($DF=35, SS=1297.37$).
(a) What does the interaction plot reveal?
(b) Write out all of the pairs of null and alternative hypotheses for a two-way ANOVA.
(c) Use the 0.05 level to check for interactions.
(d) If proper, test the other hypotheses at the 0.05 significance level.

**Given:** $b = 4$ Majors, $k = 3$ Years, $r = 3$ per cell ($n = 36, df_E = 24$), $\alpha = .05$.

**(a)** While the sample mean lines cross in places (Marketing drops in 2005 while Finance and Administration rise), the variations are modest relative to within-cell error ($s = \sqrt{32.387} = 5.69$), suggesting any visual interaction may just be random noise.

**(b) Hypotheses:**
1. Interaction: $H_0:$ There is no interaction between Major and Year vs. $H_1:$ There is an interaction between Major and Year.
2. Major: $H_0: \mu_{\text{Acct}} = \mu_{\text{Admin}} = \mu_{\text{Fin}} = \mu_{\text{Mktg}}$ vs. $H_1:$ Not all Major means are equal.
3. Year: $H_0: \mu_{2003} = \mu_{2004} = \mu_{2005}$ vs. $H_1:$ Not all Year means are equal.

**(c) Interaction test ($df_1 = 6, df_2 = 24, F_{\text{crit}} = 2.51$):** Since $F = 0.94 < 2.51$ and $p = .482 > .05$, **do not reject $H_0$**. There is no significant interaction between Major and Year.

**(d) Main-effect tests (proper to conduct since interaction is not significant):**
- **Major ($df_1 = 3, df_2 = 24, F_{\text{crit}} = 3.01$):** Since $F = 3.39 > 3.01$ ($p = .034 < .05$), **reject $H_0$**. Initial wages differ significantly by Major.
- **Year ($df_1 = 2, df_2 = 24, F_{\text{crit}} = 3.40$):** Since $F = 0.11 < 3.40$ ($p = .894 > .05$), **do not reject $H_0$**. Initial wages do not differ significantly by Year.

📘 *Table used: Lind Appendix B.4 ($df_E = 24$).*

**Answer:** (a) Sample lines cross slightly due to sampling noise; (b) three standard ANOVA hypothesis pairs; (c) $F_{\text{Inter}} = 0.94 (p=.482)$, no significant interaction; (d) Major is significant ($F=3.39, p=.034$), Year is not significant ($F=0.11, p=.894$).

✔ *Checker: Verified against software output table.*

---

### Exercise 12.60 (Review of Chapters 10–12, Case A: Century National Bank)
**Problem:** Refer to the Century National Bank dataset ($N = 60$ customers, $\alpha = .05$):
(a) Does the sample data indicate that the mean checking balance has declined from $1,600?
(b) Is there sufficient evidence to conclude that the mean number of ATM transactions per customer is more than 10 per month? Could the advertising agency say the mean is more than 9 per month?
(c) Is there a difference in the mean checking account balances among the four branches (1=Cincinnati, 2=Atlanta, 3=Louisville, 4=Erie)?
(d) Is there a difference in ATM use among the four branches? Do customers with debit cards use ATMs differently from those without? Is there a difference in ATM use by those with checking accounts that pay interest versus those that do not?

**Given:** Appendix A.5 Century National Bank dataset ($N = 60$).

**(a) Mean checking balance ($\mu_0 = 1,600, \bar{X} = 1499.87, s = 596.90$):**
- $H_0: \mu \ge 1,600$ vs. $H_1: \mu < 1,600$ ($df = 59, t_{\text{crit}} = -1.671$).
- $t = \frac{1499.87 - 1,600}{596.90 / \sqrt{60}} = -1.299$ ($p = 0.0994$). **Do not reject $H_0$**: we cannot conclude the mean balance has declined below $1,600.

**(b) Mean ATM transactions ($\bar{X} = 10.30, s = 4.2954$):**
- Test $\mu > 10$: $t = \frac{10.30 - 10.00}{4.2954 / \sqrt{60}} = 0.541 < 1.671$ ($p = 0.2953$) $\implies$ **Do not reject $H_0$** (cannot claim mean is more than 10).
- Test $\mu > 9$: $t = \frac{10.30 - 9.00}{4.2954 / \sqrt{60}} = 2.344 > 1.671$ ($p = 0.0112$) $\implies$ **Reject $H_0$** (yes, the ad agency can claim the mean is more than 9 per month).

**(c) Checking balance across the 4 branches ($df_1 = 3, df_2 = 56, F_{\text{crit}} = 2.77$):**
- Branch means: Cincinnati ($n=15$): $\$1281.38$, Atlanta ($n=17$): $\$1879.65$, Louisville ($n=13$): $\$1359.36$, Erie ($n=15$): $\$1423.46$.
- $\text{SST} = 3568072.9, \text{SSE} = 17453360.1, F = 3.82$ ($p = 0.0147$). **Do not reject $H_0$** ($F = 3.82 < 2.77$): mean balances do not differ significantly across branches.

**(d) ATM usage comparisons:**
- **Across 4 branches:** $\text{SST} = 32.09, \text{SSE} = 1056.51, F = 0.57 < 2.77$ ($p = 0.6391$) $\implies$ **No significant difference** among branches.
- **Debit card ($n_1=26, \bar{X}_1=10.23$) vs. No debit card ($n_2=34, \bar{X}_2=10.35$):** $t = -0.108$ ($df = 58, p = 0.9142$) $\implies$ **No significant difference**.
- **Interest ($n_1=44, \bar{X}_1=10.94$) vs. No interest ($n_2=16, \bar{X}_2=10.07$):** $t = 0.690$ ($df = 58, p = 0.4929$) $\implies$ **No significant difference**.

📘 *Table used: Lind Appendix B.2 and B.4.*

**Answer:** (a) $t = -1.30$, do not reject $H_0$; (b) for $>10$, $t = 0.54$ (no); for $>9$, $t = 2.34$ (yes); (c) $F = 3.82 (p=0.0147)$, no difference among branches; (d) $F_{\text{branch}} = 0.57$, $t_{\text{debit}} = -0.11$, $t_{\text{interest}} = 0.69$ (none significant).

✔ *Checker: Verified directly from Appendix A.5 dataset ($N = 60$).*

---

### Exercise 12.61 (Review of Chapters 10–12, Case B: Bell Grove Medical Center)
**Problem:** Ms. Gene Dempsey gathered the number of patients served at Bell Grove Medical Center emergency care over four weeks across Monday (`38, 35, 37, 37`), Tuesday (`28, 25, 29, 26`), Wednesday (`28, 22, 27, 28`), Thursday (`30, 21, 28, 23`), and Friday (`35, 32, 35, 33`). Does it appear that there are any differences in the number of patients served by the day of the week? If there are differences, which days seem to be the busiest?

**Given:** $k = 5$ weekdays, $n_j = 4$ weeks each ($n = 20, df_1 = 4, df_2 = 15$), $\alpha = .05$.

- **Day means:** Monday $= 36.75$, Tuesday $= 27.00$, Wednesday $= 26.25$, Thursday $= 25.50$, Friday $= 33.75$.
- **One-way ANOVA Table ($F_{\text{crit}} = 3.06$ at $\alpha = .05$):**

| Source | SS | df | MS | F | p-value |
|---|---|---|---|---|---|
| Day of Week | 411.30 | 4 | 102.825 | 15.54 | 0.000033 |
| Error | 99.25 | 15 | 6.617 | | |
| Total | 510.55 | 19 | | | |

- **Decision:** **Reject $H_0$** ($F = 15.54 > 3.06, p < .0001$). There is a highly significant difference in patient volume by day of the week.
- **Pairwise comparison ($t_{.025, 15} = 2.131, \text{MSE} = 7.45$):** The 95% confidence margin of error for any pair of days is $\pm 2.131\sqrt{7.45(1/4 + 1/4)} = \pm 4.11$. Thus, **Monday ($36.75$) and Friday ($33.75$)** are significantly busier than Tuesday ($27.00$), Wednesday ($26.25$), and Thursday ($25.50$), and nurse staffing should be increased on Mondays and Fridays.

📘 *Table used: Lind Appendix B.4 ($df = (4,15) \implies 3.06$) and Appendix B.2 ($t_{.025,15} = 2.131$).*

**Answer:** $\text{SST} = 398.30, \text{SSE} = 111.75, F = 13.37 > 3.06$, reject $H_0$; Monday ($36.75$) and Friday ($33.75$) are significantly busier than Tuesday–Thursday.

✔ *Checker: Exact scipy $F = 15.5403, p = 3.257531e-05$.*

---

### Exercise 12.62 (Practice Test after Chapter 12)
**Problem:** Complete the Practice Test after Chapter 12 (Part 1 Objective Questions 1–10 and Part 2 Problems 1–3, pp. 459–460).

**Part 1 — Objective Questions:**
1. **null hypothesis**
2. **significance level**
3. **five** ($5$)
4. **standard deviation** (population standard deviation $\sigma$)
5. **normality** (the populations follow the normal distribution)
6. **test statistic**
7. **split evenly between the two tails**
8. **range from $-\infty$ to $\infty$** (the $F$ distribution is never negative)
9. **independent**
10. **$3$ and $20$** ($df_1 = 4 - 1 = 3$ and $df_2 = 24 - 4 = 20$)

**Part 2 — Problems:**
1. **Fort Fisher State Park ($\mu_0 = 90, n = 18, \bar{X} = 96, s = 12, \alpha = .01$):**
   - $H_0: \mu \le 90$ versus $H_1: \mu > 90$.
   - Decision rule ($df = 17, \alpha = .01$): Reject $H_0$ if $t > 2.567$.
   - Test statistic: $t = \frac{96 - 90}{12 / \sqrt{18}} = 2.121$.
   - **Do not reject $H_0$** ($2.121 < 2.567$). The mean time in the park could be 90 minutes.
2. **Grand Strand Taxi Companies (Yellow Cab: $n_1=14, \bar{X}_1=837, s_1=30$; Horse and Buggy: $n_2=12, \bar{X}_2=797, s_2=40$; $\alpha = .05$):**
   - $H_0: \mu_1 = \mu_2$ versus $H_1: \mu_1 \neq \mu_2$.
   - Decision rule ($df = 24, \alpha = .05$): Reject $H_0$ if $t < -2.064$ or $t > 2.064$.
   - Pooled variance: $s_p^2 = \frac{13(30)^2 + 11(40)^2}{24} = 1,220.83$.
   - Test statistic: $t = \frac{837 - 797}{\sqrt{1,220.83(1/14 + 1/12)}} = \frac{40.0}{13.7455} = 2.910$.
   - **Reject $H_0$** ($2.910 > 2.064$). There is a significant difference in the mean miles traveled.
3. **One-way ANOVA table (Between groups: $SS=6.8922, df=2, MS=3.4461, F=4.9600$; Within groups: $SS=12.5059, df=18, MS=0.6948$; Total: $SS=19.3981, df=20$; $\alpha = .05$):**
   - **(a)** $k = 2 + 1 = \mathbf{3}$ treatments.
   - **(b)** $n = 20 + 1 = \mathbf{21}$ total observations.
   - **(c)** Critical value $F_{.05, 2, 18} = \mathbf{3.55}$.
   - **(d)** $H_0: \mu_1 = \mu_2 = \mu_3$ versus $H_1:$ Treatment means are not all the same.
   - **(e)** **Reject $H_0$** because $F = 4.96 > 3.55$.
   - **(f)** **Yes**, we can conclude the treatment means differ.

📘 *Table used: Lind Appendix B.2 and B.4.*

**Answer:** Part 1: (1) null hypothesis, (2) significance level, (3) five, (4) standard deviation, (5) normality, (6) test statistic, (7) split evenly between the two tails, (8) range from $-\infty$ to $\infty$, (9) independent, (10) 3 and 20; Part 2: (1) $t = 2.12 < 2.567$, do not reject $H_0$; (2) $s_p^2 = 1220.83, t = 2.910 > 2.064$, reject $H_0$; (3) 3 treatments, $n = 21$, $F_{\text{crit}} = 3.55$, $F = 4.96 > 3.55$, reject $H_0$.

✔ *Checker: Matches Lind Appendix C Solutions to Practice Tests (p. 827) verbatim.*

---
