set -e
INTERFACE="$(hostname -I | awk '{print $1}')"
cd guardian && bash run.sh -i mlcommons/toy_guardian:latest -n $INTERFACE -p 7900 -s 7901 -g $INTERFACE &
