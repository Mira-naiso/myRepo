#!/bin/bash

#     
VAULT_ADDRESSES=("вставьте сюда через запятую все ссылки на региональные вольты")
VAULT_TOKENS=("Вставьте сюда все токены на эти вольты через запятую")

search_for="$1"

found=false

for address in "${VAULT_ADDRESSES[@]}"; do
  for token in "${VAULT_TOKENS[@]}"; do
    mounts=$(curl -s --header "X-Vault-Token: ${token}" "${address}/v1/sys/mounts" | jq -r 'keys[]')
    for mount in $mounts; do
      value=$(curl -s --header "X-Vault-Token: ${token}" "${address}/v1/${mount}data/config")
      if [ "$value" != "null" ] && [ -n "$value" ]; then
        if echo "$value" | grep -q "$search_for"; then
          echo "Found at Address: $address, Mount: $mount" #     
          found=true #    true,   
        fi
      else
        echo "Address: $address, Mount: $mount, Value is empty or null"
      fi
    done
  done
done

if [ "$found" = false ]; then
  echo "Not Found"
fi

echo "Done"
