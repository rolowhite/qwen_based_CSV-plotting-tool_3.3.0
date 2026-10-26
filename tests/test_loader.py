"""Reading CSV files: the order of day and month in dates, and values that could not be read."""
import numpy as np
import pandas as pd

from plotstudio.data import load_csv

rng = np.random.default_rng(0)
POOL = pd.date_range("2023-01-01", "2025-12-31", freq="D")


def _dates_file(tmp_path, fmt, days, extra=()):
    path = tmp_path / "dates.csv"
    rows = [f"{i};{t.strftime(fmt)}" for i, t in enumerate(days)] + list(extra)
    path.write_text("id;when\n" + "\n".join(rows), encoding="utf-8")
    return load_csv(path)


def _mostly_small_days():
    """200 dates, 92.5% of them with a day <= 12 (they read as a date both ways)."""
    small = POOL[POOL.day <= 12][rng.permutation(int((POOL.day <= 12).sum()))[:185]]
    big = POOL[POOL.day > 12][rng.permutation(int((POOL.day > 12).sum()))[:15]]
    return small.append(big)[rng.permutation(200)]


def test_day_first_and_month_first_dates_are_never_mixed(tmp_path):
    """Review 6.1: the month-first reading was tried first and kept when 90% of the rows parsed. With 92.5% of
    the days <= 12, pandas 2+ read a day-first file month first (185 of 200 dates swapped or lost); pandas 1.x
    swapped every ambiguous date even with days spread over the month (it reads 13/01 as 13 January when asked
    for the month first, so both orders 'parse'). The order now comes from the dates themselves."""
    spread = POOL[rng.permutation(len(POOL))[:200]]
    for days in (spread, _mostly_small_days()):
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):       # day first, month first (US), ISO
            ds = _dates_file(tmp_path, fmt, days)
            got = pd.to_datetime(ds.df["when"])
            assert (got == days).all(), (fmt, int((got != days).sum()))
            ns = {"pd": pd, "np": np}
            exec("\n".join(ds.load_code), ns)                                  # the exported code reads the same
            assert (pd.to_datetime(ns["df"]["when"]) == days).all(), fmt


def test_dates_with_dots_are_day_first_even_when_every_day_is_small(tmp_path):
    days = pd.to_datetime([f"2024-{m:02d}-{d:02d}" for m in range(1, 13) for d in (1, 2, 5, 10)])
    ds = _dates_file(tmp_path, "%d.%m.%Y", days)
    assert (pd.to_datetime(ds.df["when"]) == days).all()                       # 01.02.2024 is 1 February


def test_values_that_are_not_dates_are_counted_in_a_note(tmp_path):
    """Review 6.2: values that were not dates became missing without a word (numbers already had a note)."""
    days = POOL[:200]
    ds = _dates_file(tmp_path, "%Y-%m-%d", days, extra=[f"{900 + i};not a date" for i in range(6)])
    assert ds.columns["when"].kind == "datetime" and ds.df["when"].isna().sum() == 6
    assert any("read as dates; 6 value(s) that were not dates became missing" in n for n in ds.notes), ds.notes


def test_lines_with_only_separators_above_the_header(tmp_path):
    """Review 12.3b: a first line like ",," (Excel saves empty rows that way) has no names, so 'every field looks
    like a number' was true for an empty list: the header was taken for data and the columns became col_1 ..."""
    path = tmp_path / "top.csv"
    path.write_text(",,\n,,\nage,fare,y\n30,7.25,0\n41,71.3,1\n", encoding="utf-8")
    ds = load_csv(path)
    assert list(ds.columns) == ["age", "fare", "y"] and len(ds.df) == 2 and ds.df["age"].tolist() == [30, 41]
    ns = {"pd": pd, "np": np}
    exec("\n".join(ds.load_code), ns)
    pd.testing.assert_frame_equal(ns["df"], ds.df)


def test_a_frame_with_repeated_names_gets_unique_ones():
    """Review 12.3a: dataset_from_frame() kept repeated names, and scanning df['a'] (two columns) crashed."""
    from plotstudio.data import dataset_from_frame
    ds = dataset_from_frame(pd.DataFrame([[1, 2], [3, 4]], columns=["a", "a"]))
    assert list(ds.columns) == ["a", "a (2)"] and list(ds.df.columns) == ["a", "a (2)"]
    ds = dataset_from_frame(pd.DataFrame([[1, 2], [3, 4]], columns=[1, "1"]))
    assert list(ds.columns) == ["1", "1 (2)"]


def test_european_csv(tmp_path):
    """Extra finding X1 (not in the review): with ';' between fields and decimal commas, values with dots between
    the thousands (1.234,56) became '1.234.56' and were lost as gaps whenever most of the column was below
    1,000, under a note that called them 'not numbers'."""
    rows = ["Kunden-ID;Stadt;Datum;Umsatz €;Rabatt;Notiz",
            "1;München;31.12.2024;1.234,56;12,5;",
            "2;Köln;01.02.2024;980,00;-;",
            "3;Zürich;15.03.2024;7,25;NA;",
            "4;São Paulo;28.02.2024;12.345.678,90;3;"]
    rows += [f"{i};Malmö;{(i % 28) + 1:02d}.0{(i % 9) + 1}.2024;{i * 3},{i % 100:02d};{i % 20},5;" for i in range(5, 60)]
    rows += ["60;Malmö;02.03.2024;2.5;1;", "61;Malmö;03.03.2024;12.75;1;"]        # typed with a point
    path = tmp_path / "europe.csv"
    path.write_bytes("\r\n".join(rows).encode("cp1252"))
    ds = load_csv(path)
    df = ds.df
    assert ds.sep == ";" and ds.encoding in ("cp1252", "latin-1")
    assert list(df.columns[:4]) == ["Kunden-ID", "Stadt", "Datum", "Umsatz €"]
    assert df["Stadt"].iloc[0] == "München" and df["Stadt"].iloc[3] == "São Paulo"
    assert df["Umsatz €"].tolist()[:4] == [1234.56, 980.0, 7.25, 12345678.9], ds.notes   # none lost as a gap
    assert df["Umsatz €"].tolist()[-2:] == [2.5, 12.75]                          # only dots between thousands go
    assert ds.columns["Umsatz €"].kind == "numeric" and ds.columns["Umsatz €"].missing == 0
    assert np.isnan(df["Rabatt"].iloc[1]) and np.isnan(df["Rabatt"].iloc[2]) and df["Rabatt"].iloc[0] == 12.5
    assert pd.Timestamp(df["Datum"].iloc[1]) == pd.Timestamp("2024-02-01")      # day first: 1 February
    assert ds.columns["Notiz"].kind == "empty"
    ns = {"pd": pd, "np": np}                                                    # the exported code reads it alike
    exec("\n".join(ds.load_code), ns)
    pd.testing.assert_frame_equal(ns["df"], df)


def test_decimal_commas_without_thousands_still_work(tmp_path):
    path = tmp_path / "plain.csv"
    path.write_text("a;b\n" + "\n".join(f"{i},5;{i}" for i in range(40)), encoding="utf-8")
    ds = load_csv(path)
    assert ds.df["a"].tolist()[:3] == [0.5, 1.5, 2.5] and ds.columns["a"].kind == "numeric"
