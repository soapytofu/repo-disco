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
    let n = payload.len() as u16;
    let body_and_tail = payload + tail;
    let encoded = encode_frame(payload, tail);
    assert(n as nat == payload.len());
    Varied(n).theorem_serialize_dps_parse_roundtrip(payload, tail);
    U16Le.theorem_serialize_dps_parse_roundtrip(n, body_and_tail);
    U16Le.lemma_serialize_dps_prepend(n, body_and_tail);
    U16Le.lemma_serialize_dps_len(n, body_and_tail);
    assert(U16Le.byte_len(n) == 2);
    assert(encoded == U16Le.spec_serialize_dps(n, body_and_tail));
    let prefix = choose|prefix: Seq<u8>| encoded == prefix + body_and_tail;
    assert(prefix.len() == 2);
    assert(encoded[2..] == body_and_tail);
    assert(body_and_tail[0..payload.len() as int] == payload);
    assert(body_and_tail[payload.len() as int..] == tail);
    assert(encoded[2..][payload.len() as int..] == encoded[frame_len(payload) as int..]);
    // END EDITABLE frame_roundtrip
}

} // verus!
