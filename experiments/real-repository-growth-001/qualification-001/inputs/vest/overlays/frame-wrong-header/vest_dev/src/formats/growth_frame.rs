//! Analyst reference for a bounded length-prefixed frame API.
//! Native verification is pending; this is a proposed proof-library extension.
use crate::combinators::{Bind, U16Le, Varied};
use crate::core::{proof::*, spec::*};
use vstd::prelude::*;

verus! {

pub type FrameFmt = Bind<U16Le, spec_fn(u16) -> Varied<u16>>;

pub open spec fn frame_format() -> FrameFmt {
    Bind(U16Le, |n: u16| Varied(n))
}

pub open spec fn payload_fits(payload: Seq<u8>) -> bool {
    payload.len() <= 65535
}

pub open spec fn frame_value(payload: Seq<u8>) -> (u16, Seq<u8>) {
    (payload.len() as u16, payload)
}

pub open spec fn frame_len(payload: Seq<u8>) -> nat {
    2 + payload.len()
}

pub open spec fn encode_frame(payload: Seq<u8>, tail: Seq<u8>) -> Seq<u8> {
    frame_format().spec_serialize_dps(frame_value(payload), tail)
}

pub open spec fn decode_frame(input: Seq<u8>) -> Option<(int, Seq<u8>)> {
    match frame_format().spec_parse(input) {
        Some((used, (_, payload))) => Some((used, payload)),
        None => None,
    }
}

pub proof fn frame_roundtrip(payload: Seq<u8>, tail: Seq<u8>)
    requires
        payload_fits(payload),
    ensures
        decode_frame(encode_frame(payload, tail))
            == Some((frame_len(payload) as int, payload)),
        encode_frame(payload, tail).len() == frame_len(payload) + tail.len(),
        encode_frame(payload, tail)[frame_len(payload) as int..] == tail,
{
    // BEGIN EDITABLE frame_roundtrip
    let fmt = frame_format();
    // A zero length header is not consistent with an arbitrary nonempty payload.
    fmt.theorem_serialize_dps_parse_roundtrip((0u16, payload), tail);
    // END EDITABLE frame_roundtrip
}

} // verus!
