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
if payloads.len() == 0 {
} else {
    let first = payloads[0];
    let rest = payloads.drop_first();
    frame_roundtrip(first, encode_batch(rest, tail));
    batch_roundtrip(rest, tail);
    let encoded_rest = encode_batch(rest, tail);
    let encoded = encode_frame(first, encoded_rest);
    assert(encoded == encode_batch(payloads, tail));
    let n_first = frame_len(first) as int;
    let n_rest = batch_len(rest) as int;
    assert(decode_frame(encoded) == Some((n_first, first)));
    assert(encoded.len() == frame_len(first) + encoded_rest.len());
    assert(encoded[n_first..] =~= encoded_rest);
    assert(decode_batch(encoded_rest, rest.len()) == Some((n_rest, rest)));
    assert(encoded_rest.len() == batch_len(rest) + tail.len());
    assert(encoded_rest[n_rest..] =~= tail);
    assert(0 <= n_first <= encoded.len());
    assert(decode_batch(encoded[n_first..], (payloads.len() - 1) as nat) == Some((n_rest, rest)));
    assert(n_first + n_rest == batch_len(payloads) as int);
    assert(seq![first] + rest =~= payloads);
    assert(decode_batch(encoded, payloads.len()) == Some((batch_len(payloads) as int, payloads)));
    assert(encoded.len() == batch_len(payloads) + tail.len());
    assert(encoded[batch_len(payloads) as int..] =~= tail);
}
    // END EDITABLE batch_roundtrip
}

} // verus!
