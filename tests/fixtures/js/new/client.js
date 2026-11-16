const TIMEOUT = 15;
const defaultConfig = {
  timeout: 15.0,
  retries: 3,
  nested: {
    size: 16,
  },
};

function request(url, timeout = 15.0, retries = 3) {
  return [url, timeout, retries];
}

const connect = (host, delay = 100) => host;
