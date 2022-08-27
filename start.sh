#! /bin/bash
    _cputype="$(uname -m)"



    case "$_cputype" in
        x86_64 | x86-64 | x64 | amd64)
            _cputype=x86_64
            mv /yagna/amd64/yagna /root/.local/bin/yagna
            mv /yagna/amd64/gftp /root/.local/bin/gftp
            ;;
        arm64 | aarch64)
            _cputype=aarch64
            mv /yagna/arm64/yagna /root/.local/bin/yagna
            mv /yagna/arm64/gftp /root/.local/bin/gftp
            ;;
        *)
            err "invalid cputype: $_cputype"
            ;;
    esac


get_funds_from_faucet () {
  FUNDING_STATUS=$(/root/.local/bin/yagna payment fund)
}


echo "Starting Yagna"
RUST_LOG=error MARKET_DB_CLEANUP_INTERVAL=10min /root/.local/bin/yagna service run > /dev/null 2>&1 &
sleep 1


key=$(/root/.local/bin/yagna app-key create requester)
echo "Key: $key"

# Acquire funds
get_funds_from_faucet
if [[ $FUNDING_STATUS == *"deadline has elapsed"* ]]; then
  echo "Error receiving funds from the faucet. We're retrying..."
  while [[ $FUNDING_STATUS == *"deadline has elapsed"* ]]
  do
    get_funds_from_faucet
  done
fi

# Init payments account
/root/.local/bin/yagna payment init --sender