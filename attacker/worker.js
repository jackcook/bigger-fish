const OUR_ATTACKER = "ours";
const CACHE_ATTACKER = "cache";
const OUR_ATTACKER_COUNTERMEASURE = "ours_cm";

const P = 5; // time of one record, in milliseconds
const L3_SIZE = 6 * 1024 * 1024;
const CACHE_SIZE = L3_SIZE / 64;

let addrs;
let M;
let start;
let T;
let recording = false;

function finish() {
  if (!recording) {
    return;
  }

  recording = false;

  let lastVal = 0;

  for (let i = 0; i < T.length; i++) {
    if (T[i] === -1) {
      T[i] = lastVal;
    } else {
      lastVal = T[i];
    }
  }

  postMessage(JSON.stringify(T));
}

function ourLoop() {
  while (true) {
    const datum_time = performance.now();
    const idx = Math.floor(datum_time - start);

    if (idx >= T.length) {
      finish();
      break;
    }

    let counter = 0;

    while (performance.now() - datum_time < P) {
      counter += 1;
    }

    T[idx] = counter;
  }
}

function cacheLoop() {
  while (true) {
    const datum_time = performance.now();
    const idx = Math.floor(datum_time - start);

    if (idx >= T.length) {
      finish();
      break;
    }

    let counter = 0;

    while (performance.now() - datum_time < P) {
      // Access entire LLC
      let val = 0;
      for (let i = 0; i < addrs.length; i++) {
        val = M[addrs[i] * 16];
      }

      counter += 1;
    }

    T[idx] = counter;
  }
}

// Randomized timer
let time = 0;
let currentBinSize = 0;

const randomBinSize = () => {
  return Math.random() * 50 + 5;
};

const getTime = () => {
  const now = performance.now();

  if (now > time + currentBinSize) {
    if (now > time + currentBinSize + 100) {
      time = now;
    }

    time += randomBinSize();
    currentBinSize = randomBinSize();
  }

  return time;
};

function countermeasureLoop() {
  while (true) {
    const datum_time = getTime();
    const idx = Math.floor(datum_time - start);

    if (idx >= T.length) {
      finish();
      break;
    }

    let counter = 0;

    while (getTime() - datum_time < P) {
      counter += 1;
    }

    T[idx] = counter;
  }
}

function record(attacker) {
  if (attacker === CACHE_ATTACKER) {
    M = new Int32Array(L3_SIZE / 4);
    M.fill(-1, 0, M.length);

    addrs = new Int32Array(L3_SIZE / 4 / 16);

    for (let i = 0; i < addrs.length; i++) {
      addrs[i] = i;
    }

    // Shuffle addrs
    for (let i = addrs.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const temp = addrs[i];
      addrs[i] = addrs[j];
      addrs[j] = temp;
    }
  }

  start = performance.now();

  switch (attacker) {
    case OUR_ATTACKER:
      ourLoop();
      break;
    case CACHE_ATTACKER:
      cacheLoop();
      break;
    case OUR_ATTACKER_COUNTERMEASURE:
      countermeasureLoop();
      break;
    default:
      finish();
      break;
  }
}

self.onmessage = (e) => {
  if (e.data.type == "stop") {
    finish();
  } else if (e.data.type == "start") {
    T = new Array(e.data.trace_length);
    T.fill(-1, 0, e.data.trace_length);

    recording = true;
    start = performance.now();
    setTimeout(record, 0, e.data.attacker);
  }
};
