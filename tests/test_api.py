from fastapi.testclient import TestClient

from backend import main


client = TestClient(main.app)


def test_health_and_bundled_observation_endpoints():
    health = client.get("/api/health")
    response = client.get("/api/observations")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    payload = response.json()
    assert payload["count"] == 11
    assert payload["rows"][0]["date"] == "2003-01-15"
    assert payload["rows"][0]["chlorophyll_source_file"].endswith(".nc")


def test_metadata_model_info_and_simulation_bounds():
    metadata = client.get("/api/metadata")
    model_info = client.get("/api/model-info")
    invalid_simulation = client.get("/api/npzd?days=0")

    assert metadata.status_code == 200
    assert metadata.json()["observation_count"] == 11
    assert metadata.json()["offline"] is True
    assert metadata.json()["sst_mean_c"] > 0
    assert model_info.status_code == 200
    assert len(model_info.json()["states"]) == 4
    assert model_info.json()["bayesian_method"] == "Random-walk Metropolis-Hastings in log-parameter space"
    assert invalid_simulation.status_code == 422


def test_model_and_saved_posterior_endpoints_return_real_artifacts():
    simulation = client.get("/api/npzd?days=14")
    posterior = client.get("/api/posterior")
    uncertainty = client.get("/api/prediction-uncertainty")

    assert simulation.status_code == 200
    assert simulation.json()["count"] == 15
    assert all(row["phytoplankton"] >= 0 for row in simulation.json()["rows"])
    assert posterior.json()["draw_count"] == 6000
    assert len(posterior.json()["parameters"]) == 5
    assert "samples" not in posterior.json()
    distribution = client.get("/api/posterior/distribution/growth_rate_day")
    invalid_distribution = client.get("/api/posterior/distribution/not-a-parameter")
    assert distribution.status_code == 200
    assert len(distribution.json()["bins"]) == 40
    assert distribution.json()["credible_interval_2_5"] <= distribution.json()["median"]
    assert invalid_distribution.status_code == 404
    assert len(uncertainty.json()["rows"]) == 366


def test_uploaded_dataset_can_be_retrieved_and_deleted():
    uploaded = client.post(
        "/api/uploads",
        files={
            "file": (
                "observations.csv",
                b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,7.5,3.6\n",
                "text/csv",
            )
        },
    )
    upload_id = uploaded.json()["upload_id"]

    retrieved = client.get(f"/api/uploads/{upload_id}")
    deleted = client.delete(f"/api/uploads/{upload_id}")
    missing = client.get(f"/api/uploads/{upload_id}")

    assert retrieved.status_code == 200
    assert retrieved.json()["rows"][0]["sst_c"] == 7.5
    assert deleted.json() == {"deleted": True}
    assert missing.status_code == 404


def test_csv_upload_validation_and_date_specific_prediction():
    uploaded = client.post(
        "/api/uploads",
        files={
            "file": (
                "observations.csv",
                b"date,sst_c,chlorophyll_mg_m3\n"
                b"2003-02-15,6.8,0.7\n"
                b"2003-01-15,7.5,3.6\n",
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 200
    upload_data = uploaded.json()
    assert upload_data["count"] == 2
    assert upload_data["rows"][0]["date"] == "2003-01-15"

    prediction = client.post(
        "/api/predictions",
        json={
            "dataset": "uploaded",
            "upload_id": upload_data["upload_id"],
            "target_date": "2003-01-15",
        },
    )
    assert prediction.status_code == 200
    result = prediction.json()
    assert result["observed_sst_c"] == 7.5
    assert result["observed_chlorophyll_mg_m3"] == 3.6
    assert 0 < result["lower_95"] <= result["median"] <= result["upper_95"]
    assert result["is_future_forecast"] is False


def test_prediction_rejects_uploaded_year_with_insufficient_sst():
    uploaded = client.post(
        "/api/uploads",
        files={
            "file": (
                "single-date.csv",
                b"date,sst_c,chlorophyll_mg_m3\n2003-01-15,7.5,3.6\n",
                "text/csv",
            )
        },
    )
    response = client.post(
        "/api/predictions",
        json={
            "dataset": "uploaded",
            "upload_id": uploaded.json()["upload_id"],
            "target_date": "2003-01-15",
        },
    )

    assert response.status_code == 422
    assert "At least two SST observations" in response.json()["detail"]


def test_csv_upload_rejects_missing_required_columns():
    response = client.post(
        "/api/uploads",
        files={"file": ("invalid.csv", b"date,sst_c\n2003-01-15,7.5\n", "text/csv")},
    )
    assert response.status_code == 422
    assert "Missing required columns" in response.json()["detail"]


def test_fresh_estimation_endpoint_uses_model_and_updates_in_memory(monkeypatch):
    observed = {}
    monkeypatch.setattr(main, "runtime_posterior", None)
    monkeypatch.setattr(main, "runtime_predictive", None)
    monkeypatch.setattr(main, "runtime_diagnostics", None)
    monkeypatch.setattr(main, "runtime_acceptance", None)

    def fake_estimation(data, draws, burn_in, seed, chains):
        observed.update(draws=draws, burn_in=burn_in, seed=seed, chains=chains)
        posterior = main.BUNDLED_POSTERIOR.head(20).copy()
        posterior.attrs["acceptance_rates"] = [0.2, 0.21, 0.19, 0.2]
        posterior.attrs["chain_samples"] = posterior.to_numpy().reshape(4, 5, 5)
        return posterior, 0.2

    monkeypatch.setattr(main, "run_bayesian_estimation", fake_estimation)
    monkeypatch.setattr(main, "sampling_diagnostics", lambda posterior: main.BUNDLED_DIAGNOSTICS.copy())
    monkeypatch.setattr(main, "posterior_predictive", lambda *args, **kwargs: main.BUNDLED_PREDICTIVE.copy())

    response = client.post("/api/bayesian/estimate")

    assert response.status_code == 200
    assert observed == {"draws": 1200, "burn_in": 300, "seed": 2026, "chains": 4}
    assert response.json()["fresh_estimate"] is True
    assert response.json()["draw_count"] == 20
