include "RepoDiscoFramePair.dfy"

module RepoDiscoTaggedFramePair {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import P = RepoDiscoFramePair
  import opened Wrappers

  datatype TaggedPair = TaggedPair(payload: seq<U.uint8>, companion: seq<U.uint8>, rest: seq<U.uint8>)

  predicate method IsTaggedBounded(input: seq<U.uint8>, tag: U.uint8, budget: nat) {
    P.HasFramePair(input) &&
      0 < |F.FramePayload(input)| &&
      F.FramePayload(input)[0] == tag &&
      |F.FramePayload(input)| - 1 + |F.FramePayload(F.FrameRest(input))| <= budget
  }

  function method {:opaque} ReadTaggedBoundedPair(input: seq<U.uint8>, tag: U.uint8, budget: nat)
    : (result: Result<TaggedPair, string>)
    ensures result.Success? <==> IsTaggedBounded(input, tag, budget)
    ensures result.Success? ==> result.value.payload == F.FramePayload(input)[1..]
    ensures result.Success? ==> result.value.companion == F.FramePayload(F.FrameRest(input))
    ensures result.Success? ==> result.value.rest == F.FrameRest(F.FrameRest(input))
    ensures result.Success? ==> |result.value.payload| + |result.value.companion| <= budget
    ensures result.Success? ==>
      U.HasUint16Len([tag] + result.value.payload) && U.HasUint16Len(result.value.companion)
    ensures result.Success? ==>
      input == U.UInt16ToSeq(|[tag] + result.value.payload| as U.uint16) + [tag] + result.value.payload +
               U.UInt16ToSeq(|result.value.companion| as U.uint16) + result.value.companion + result.value.rest
  {
    // BEGIN REPLACEMENT
    var parsed := P.ReadFramePair(input);
    if parsed.Failure? then
      Failure(parsed.error)
    else
      var pair := parsed.value;
      if |pair.left| == 0 then
        Failure("Missing tag")
      else
        var payload := pair.left[1..];
        if |payload| + |pair.right| > budget then
          Failure("Payload budget exceeded")
        else
          assert P.HasFramePair(input);
          assert pair.left == F.FramePayload(input);
          assert pair.right == F.FramePayload(F.FrameRest(input));
          assert pair.rest == F.FrameRest(F.FrameRest(input));
          assert pair.left == [tag] + payload;
          assert IsTaggedBounded(input, tag, budget);
          assert U.HasUint16Len([tag] + payload);
          assert U.HasUint16Len(pair.right);
          assert input == U.UInt16ToSeq(|[tag] + payload| as U.uint16) + [tag] + payload +
                          U.UInt16ToSeq(|pair.right| as U.uint16) + pair.right + pair.rest;
          Success(TaggedPair(payload, pair.right, pair.rest))
    // END REPLACEMENT
  }
}
