set -e
bash generate_user_keys.sh
bash start_policy_engine.sh
bash start_guardian.sh
bash start_ui_apps.sh