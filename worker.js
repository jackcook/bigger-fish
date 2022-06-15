const P = 5; // time of one record, in milliseconds

let start;
let T;
let recording = false;
// let updateInterval = 500;
let lastUpdateTime = 0;

function sendUpdate(done) {
  if (!recording) {
    return;
  }

  if (done) {
    recording = false;
  }

  let trace = [...T];
  let lastVal = 0;

  for (let i = 0; i < T.length; i++) {
    if (trace[i] === -1) {
      trace[i] = lastVal;
    } else {
      lastVal = trace[i];
    }
  }

  postMessage(
    JSON.stringify({
      done,
      maxIndex: Math.floor(performance.now() - start),
      trace,
    })
  );
}

function record() {
  start = performance.now();
  lastUpdateTime = performance.now();

  while (true) {
    const datum_time = performance.now();
    const idx = Math.floor(datum_time - start);

    if (idx >= T.length) {
      sendUpdate(true);
      break;
    }

    let counter = 0;

    while (performance.now() - datum_time < P) {
      counter += 1;
    }

    T[idx] = counter;

    // if (performance.now() - lastUpdateTime > updateInterval) {
    //   sendUpdate(false);
    //   lastUpdateTime = performance.now();
    // }
  }
}

self.onmessage = (e) => {
  if (e.data.type == "stop") {
    finish();
  } else if (e.data.type == "start") {
    T = new Array(e.data.traceLength);
    T.fill(-1, 0, e.data.traceLength);

    recording = true;
    start = performance.now();
    setTimeout(record, 0);
  }
};
