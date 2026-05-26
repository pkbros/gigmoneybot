# 🚀 SkillToken Cloud Deployment Guide

This guide contains the exact commands to build and deploy the SkillToken Telegram bot to Google Cloud Run.

## 🛠 Prerequisites
Ensure you are logged into the Google Cloud CLI:
```bash
gcloud auth login
gcloud config set project geeksforgeekstut
```

---

## 🏗 Step 1: Build the Container
Use Google Cloud Build to create a Docker image and push it to the Artifact Registry. Replace `v13` with your new version number (e.g., `v14`, `v15`).

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/geeksforgeekstut/skill-token-repo/skill-token:v13 .
```

## 🚀 Step 2: Deploy to Cloud Run
Deploy the newly built image to the live service. Ensure `env.yaml` is present in your directory to inject environment variables.

```bash
gcloud run deploy skill-token \
  --image us-central1-docker.pkg.dev/geeksforgeekstut/skill-token-repo/skill-token:v13 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --env-vars-file env.yaml \
  --timeout=300 \
  --quiet
```

---

## 📋 Summary of Parameters
| Parameter | Description |
| :--- | :--- |
| `--tag` | The full path to the image in Artifact Registry. |
| `--image` | Tells Cloud Run which built image to use for the deployment. |
| `--env-vars-file` | Path to your `env.yaml` containing secrets (Bot Token, DB Key, etc). |
| `--timeout` | Set to `300` to allow for cold starts or heavy initial processing. |

## 🔍 Checking Logs
If the bot isn't responding, check the real-time logs:
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=skill-token" --limit 20
```
