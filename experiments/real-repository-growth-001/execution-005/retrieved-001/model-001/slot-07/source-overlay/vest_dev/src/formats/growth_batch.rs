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
    assert(encode_batch(payloads, tail) == tail);
    assert(decode_batch(tail, 0) == Some((0int, Seq::empty())));
    assert(batch_len(payloads) == 0);
    assert(encode_batch(payloads, tail).len() == batch_len(payloads) + tail.len());
    assert(encode_batch(payloads, tail)[batch_len(payloads) as int..] =~= tail);
} else {
    let first = payloads[0];
    let rest = payloads.drop_first();
    assert(payload_fits(first));
    assert(batch_fits(rest));
    batch_roundtrip(rest, tail);
    let rest_encoded = encode_batch(rest, tail);
    assert(decode_batch(rest_encoded, rest.len()) == Some((batch_len(rest) as int, rest)));
    assert(rest_encoded.len() == batch_len(rest) + tail.len());
    assert(rest_encoded[batch_len(rest) as int..] =~= tail);
    frame_roundtrip(first, rest_encoded);
    let full_encoded = encode_frame(first, rest_encoded);
    assert(decode_frame(full_encoded) == Some((frame_len(first) as int, first)));
    assert(full_encoded.len() == frame_len(first) + rest_encoded.len());
    assert(full_encoded[frame_len(first) as int..] =~= rest_encoded);
    let n_frame = frame_len(first) as int;
    assert(full_encoded[n_frame..] == rest_encoded);
    assert(decode_batch(full_encoded[n_frame..], rest.len()) == Some((batch_len(rest) as int, rest)));
    assert(encode_batch(payloads, tail) == full_encoded);
    assert(batch_len(payloads) == frame_len(first) + batch_len(rest));
    let total = batch_len(payloads) as int;
    assert(decode_batch(full_encoded, payloads.len()) == Some((total, payloads))) by {
        assert(0 <= n_frame <= full_encoded.len());
        assert(seq![first] + rest =~= payloads);
    }
    assert(full_encoded.len() == batch_len(payloads) + tail.len());
    assert(full_encoded[total..] =~= tail) by {
        assert(full_encoded[n_frame..] =~= rest_encoded);
        assert(rest_encoded[batch_len(rest) as int..] =~= tail);
        assert(total == n_frame + batch_len(rest) as int);
        assert(full_encoded[total..] =~= full_encoded[n_frame..][batch_len(rest) as int..]);
    }
}
    // END EDITABLE batch_roundtrip
}

} // verus!
