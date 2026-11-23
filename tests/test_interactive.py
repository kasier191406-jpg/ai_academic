import pandas as pd
import pytest

from src.interactive import posterior_prediction_for_date, validate_uploaded_csv
from src.model import load_observations


def test_upload_csv_is_sorted_and_keeps_only_required_columns():
    content = (
        b"date,sst_c,chlorophyll_mg_m3,source\n"
        b"2003-02-15,6.8,0.7,second\n"
        b"2003-01-15,7.5,3.6,first\n"
    )

    observations = validate_uploaded_csv(content)

    assert observations.columns.tolist() == ["date", "sst_c", "chlorophyll_mg_m3"]
    assert observations["date"].tolist() == [
        pd.Timestamp("2003-01-15"),
        pd.Timestamp("2003-02-15"),
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"date,sst_c\n2003-01-15,7.5\n", "Missing required columns"),
        (
            b"date,sst_c,chlorophyll_mg_m3\n2003-02-30,7.5,1.0\n",
            "invalid dates",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n20030115,7.5,1.0\n",
            "date strings",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n2003-01-15T00:00:00Z,7.5,1.0\n",
            "timezone-free",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,warm,1.0\n",
            "finite numerical values",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,,1.0\n",
            "Missing values",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,7.5,-1.0\n",
            "cannot be negative",
        ),
        (
            b"date,sst_c,chlorophyll_mg_m3\n"
            b"2003-01-15,7.5,1.0\n"
            b"2003-01-15,7.6,1.1\n",
            "must be unique",
        ),
    ],
)
def test_upload_csv_rejects_invalid_data(content, message):
    with pytest.raises(ValueError, match=message):
        validate_uploaded_csv(content)


def test_upload_csv_rejects_empty_or_malformed_files():
    for content in (b"", b"date,sst_c,chlorophyll_mg_m3\n"):
        with pytest.raises(ValueError):
            validate_uploaded_csv(content)


def test_bundled_dataset_has_a_date_specific_model_prediction():
    posterior = pd.read_csv("data/processed/posterior_samples.csv").head(20)
    observations = load_observations()
    date = observations.loc[0, "date"]

    prediction = posterior_prediction_for_date(posterior, observations, date)

    assert 0 < prediction["lower_95"] <= prediction["median"] <= prediction["upper_95"]


def test_uploaded_dataset_prediction_uses_sst_but_not_uploaded_chlorophyll():
    posterior = pd.read_csv("data/processed/posterior_samples.csv").head(20)
    uploaded = validate_uploaded_csv(
        b"date,sst_c,chlorophyll_mg_m3\n"
        b"2003-01-15,7.5,1.0\n"
        b"2003-06-15,22.0,2.0\n"
        b"2003-12-15,10.4,3.0\n"
    )
    changed_chlorophyll = uploaded.assign(chlorophyll_mg_m3=[10.0, 20.0, 30.0])

    prediction = posterior_prediction_for_date(
        posterior, uploaded, pd.Timestamp("2003-06-15")
    )
    changed_prediction = posterior_prediction_for_date(
        posterior, changed_chlorophyll, pd.Timestamp("2003-06-15")
    )

    assert prediction == changed_prediction
    assert prediction["lower_95"] <= prediction["median"] <= prediction["upper_95"]


def test_uploaded_dataset_prediction_explains_insufficient_sst_data():
    posterior = pd.read_csv("data/processed/posterior_samples.csv").head(20)
    uploaded = validate_uploaded_csv(
        b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,7.5,1.0\n"
    )

    with pytest.raises(ValueError, match="At least two SST observations"):
        posterior_prediction_for_date(
            posterior, uploaded, pd.Timestamp("2003-01-15")
        )
