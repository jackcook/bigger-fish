use byteorder::{NativeEndian, ReadBytesExt};
use std::collections::BTreeMap;
use std::io::Cursor;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use structopt::StructOpt;

#[derive(Debug, StructOpt)]
#[structopt(name = "ebpf-interrupts", about = "Record IRQs using eBPF")]
struct Opt {
    #[structopt(short, long)]
    timeout: Option<u64>,

    #[structopt(short, long)]
    ns_threshold: Option<u64>,
}

const MAX_SAMPLES: usize = 1000000;

fn time() -> u64 {
    let mut t = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    unsafe {
        libc::clock_gettime(libc::CLOCK_BOOTTIME, &mut t as *mut libc::timespec);
    }

    t.tv_sec as u64 * 1000_000_000 + t.tv_nsec as u64
}

fn main() {
    core_affinity::set_for_current(core_affinity::CoreId { id: 3 });

    eprintln!("pid = {}", unsafe { libc::getpid() });

    let opt = Opt::from_args();

    let running = Arc::new(AtomicBool::new(true));
    let r = running.clone();
    ctrlc::set_handler(move || {
        r.store(false, Ordering::SeqCst);
    })
    .expect("Error setting Ctrl-C handler");

    let mut gaps = vec![(1, 1); MAX_SAMPLES];
    gaps.clear();

    let code = "
#include <uapi/linux/ptrace.h>

BPF_HASH(interrupts, u64, int, 1000000);
static void record_event(int num) {
    if (bpf_get_smp_processor_id() == 3) {
        int irq = num;
        u64 time = bpf_ktime_get_boot_ns();
        interrupts.update(&time, &irq);
    }
}

TRACEPOINT_PROBE(irq, irq_handler_entry) {
    record_event(args->irq + 10000);
    return 0;
};
TRACEPOINT_PROBE(irq, softirq_entry) {
    record_event(1);
    return 0;
};
TRACEPOINT_PROBE(nmi, nmi_handler) {
    record_event(2);
    return 0;
};
TRACEPOINT_PROBE(tlb, tlb_flush) {
    record_event(3);
    return 0;
};
TRACEPOINT_PROBE(irq_vectors, reschedule_entry) {
    record_event(4);
    return 0;
};
TRACEPOINT_PROBE(syscalls, sys_enter_clock_gettime) {
    record_event(5);
    return 0;
};
TRACEPOINT_PROBE(exceptions, page_fault_user) {
    record_event(6);
    return 0;
};
TRACEPOINT_PROBE(exceptions, page_fault_kernel) {
    record_event(7);
    return 0;
};
void generic_handle_irq() { record_event(100); }
void __sysvec_apic_timer_interrupt() { record_event(101); }
void __sysvec_spurious_apic_interrupt() { record_event(102); }
void __sysvec_call_function() { record_event(103); }
void __sysvec_call_function_single() { record_event(104); }
void __sysvec_x86_platform_ipi() { record_event(105); }
void __sysvec_thermal() { record_event(106); }
void __sysvec_irq_work() { record_event(107); }
void __sysvec_deferred_error() { record_event(108); }
void __sysvec_threshold() { record_event(109); }
void __sysvec_irq_move_cleanup() { record_event(110); }
void __sysvec_error_interrupt() { record_event(111); }
void __do_softirq() { record_event(200); }
void irqtime_account_irq() { record_event(300); }
";
    let mut module = bcc::BPF::new(code).unwrap();
    bcc::Tracepoint::new()
        .handler("tracepoint__irq__irq_handler_entry")
        .subsystem("irq")
        .tracepoint("irq_handler_entry")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__irq__softirq_entry")
        .subsystem("irq")
        .tracepoint("softirq_entry")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__nmi__nmi_handler")
        .subsystem("nmi")
        .tracepoint("nmi_handler")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__tlb__tlb_flush")
        .subsystem("tlb")
        .tracepoint("tlb_flush")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__irq_vectors__reschedule_entry")
        .subsystem("irq_vectors")
        .tracepoint("reschedule_entry")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__syscalls__sys_enter_clock_gettime")
        .subsystem("syscalls")
        .tracepoint("sys_enter_clock_gettime")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__exceptions__page_fault_user")
        .subsystem("exceptions")
        .tracepoint("page_fault_user")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    bcc::Tracepoint::new()
        .handler("tracepoint__exceptions__page_fault_kernel")
        .subsystem("exceptions")
        .tracepoint("page_fault_kernel")
        .attach(&mut module)
        .expect("failed to attach tracepoint");

    for interrupt in [
        "generic_handle_irq",
        "__sysvec_apic_timer_interrupt",
        "__sysvec_spurious_apic_interrupt",
        "__sysvec_call_function",
        "__sysvec_call_function_single",
        "__sysvec_x86_platform_ipi",
        "__sysvec_thermal",
        "__sysvec_irq_work",
        "__sysvec_deferred_error",
        "__sysvec_threshold",
        "__sysvec_irq_move_cleanup",
        "__sysvec_error_interrupt",
        // "__do_softirq",
        // "irqtime_account_irq",
    ] {
        bcc::Kprobe::new()
            .handler(interrupt)
            .function(interrupt)
            .attach(&mut module)
            .unwrap();
    }

    let table = module.table("interrupts").expect("failed to get table");

    let start_time = time();
    let end_time = start_time + opt.timeout.unwrap_or(5000) * 1000000;

    let mut t = start_time;
    while t < end_time {
        let t2 = time();
        if t2 - t > opt.ns_threshold.unwrap_or(500) {
            gaps.push((t - start_time, t2 - t));
            t = time();
        } else {
            t = t2;
        }
    }

    let mut counts = BTreeMap::new();
    let mut irq_times = Vec::new();
    for e in &table {
        let key = Cursor::new(e.key).read_u64::<NativeEndian>().unwrap();
        let value = Cursor::new(e.value).read_i32::<NativeEndian>().unwrap();
        if key > start_time && key < t {
            irq_times.push((key - start_time, value));
            *counts.entry(value).or_insert(0) += 1;
        }
    }

    irq_times.sort_by_key(|(t, _)| *t);

    eprintln!("{:#?}", counts);

    let mut gap_sequence: BTreeMap<_, Vec<_>> = BTreeMap::new();

    let total_gaps = gaps.len();
    let mut explained_gaps = 0;

    for (start, length) in gaps {
        let irq_index = irq_times.binary_search_by(|(t, _kind)| {
            if *t < start - 150 {
                std::cmp::Ordering::Less
            } else if *t > start + length + 150 {
                std::cmp::Ordering::Greater
            } else {
                std::cmp::Ordering::Equal
            }
        });

        if let Ok(irq_index) = irq_index {
            let (t, kind) = irq_times[irq_index];
            gap_sequence.entry(kind).or_default().push(t);
            explained_gaps += 1;
        }
    }

    println!("{:.2}", explained_gaps as f32 / total_gaps as f32 * 100.0);
    for (kind, gaps) in gap_sequence {
        print!("{}", kind);
        for g in gaps {
            print!(" {}", g);
        }
        println!();
    }
    eprintln!("{}/{}", irq_times.len(), total_gaps);
}
