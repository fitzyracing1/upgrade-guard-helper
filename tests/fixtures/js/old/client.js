const TIMEOUT = 5;
const defaultConfig = {
  timeout: 5.0,
  retries: 3,
  nested: {
    size: 8,
  },
};

function request(url, timeout = 5.0, retries = 3) {
  return [url, timeout, retries];
}

const connect = (host, delay = 100) => host;
