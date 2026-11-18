//! Analyst reference for a counted stream of accepted length-prefixed frames.
//! The count is supplied out of band; no runtime parser or on-wire count is claimed.
use super::growth_frame::*;
use vstd::prelude::*;

verus! {

pub open spec fn batch_fits(payloads: Seq<Seq<u8>>) -> bool
    decreases payloads.len(),
{
    payloads.len() == 0 || (
        payload_fits(payloads[0]) && batch_fits(payloads.drop_first())
    )
}

pub open spec fn batch_len(payloads: Seq<Seq<u8>>) -> nat
    decreases payloads.len(),
{
    if payloads.len() == 0 { 0 }
    else { frame_len(payloads[0]) + batch_len(payloads.drop_first()) }
}

pub open spec fn encode_batch(payloads: Seq<Seq<u8>>, tail: Seq<u8>) -> Seq<u8>
    decreases payloads.len(),
{
    if payloads.len() == 0 { tail }
    else { encode_frame(payloads[0], encode_batch(payloads.drop_first(), tail)) }
}

pub open spec fn decode_batch(input: Seq<u8>, count: nat)
    -> Option<(int, Seq<Seq<u8>>)>
    decreases count,
{
    if count == 0 {
        Some((0int, Seq::empty()))
    } else {
        match decode_frame(input) {
            Some((used, first)) => {
                if 0 <= used <= input.len() {
                    match decode_batch(input[used..], (count - 1) as nat) {
                        Some((rest_used, rest)) => Some((used + rest_used, seq![first] + rest)),
                        None => None,
                    }
                } else { None }
            },
            None => None,
        }
    }
}

pub proof fn batch_roundtrip(payloads: Seq<Seq<u8>>, tail: Seq<u8>)
    requires
        batch_fits(payloads),
    ensures
        decode_batch(encode_batch(payloads, tail), payloads.len())
            == Some((batch_len(payloads) as int, payloads)),
        encode_batch(payloads, tail).len() == batch_len(payloads) + tail.len(),
        encode_batch(payloads, tail)[batch_len(payloads) as int..] == tail,
    decreases payloads.len(),
{
    // BEGIN EDITABLE batch_roundtrip
    if payloads.len() > 0 {
        // Parsing zero frames cannot recover a nonempty payload list.
        assert(decode_batch(encode_batch(payloads, tail), 0)
            == Some((batch_len(payloads) as int, payloads)));
    }
    // END EDITABLE batch_roundtrip
}

} // verus!
