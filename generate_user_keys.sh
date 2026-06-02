set -e

: "${USER_KEYS_FOLDER?Missing environment variable USER_KEYS_FOLDER}"

# create user keys
mkdir -p ${USER_KEYS_FOLDER}
for i in 1 2 3 4 5 ; do
    if [ ! -f ${USER_KEYS_FOLDER}/user${i}_private.pem ] ; then
        docker run --rm --volume ${USER_KEYS_FOLDER}:/tmp/users_keys \
            --entrypoint /project/pdo/run/bin/python pdo_client:0.4.29 \
            /project/pdo/src/build/__tools__/make-keys \
            --keyfile /tmp/users_keys/user${i} --format pem
    fi
done