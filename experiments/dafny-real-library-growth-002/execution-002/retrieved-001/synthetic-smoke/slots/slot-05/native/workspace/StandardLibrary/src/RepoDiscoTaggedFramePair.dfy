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
0 // SYNTHETIC plumbing only, not a native proof 5
    // END REPLACEMENT
  }
}
