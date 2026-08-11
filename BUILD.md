cd backend

python bump_version.py

gcloud config set project lucidex-502504

gcloud run deploy api --source . --region asia-southeast1 --allow-unauthenticated

adb logcat -c; adb logcat | Select-String "flutter|ApiClient|Response|Request"
