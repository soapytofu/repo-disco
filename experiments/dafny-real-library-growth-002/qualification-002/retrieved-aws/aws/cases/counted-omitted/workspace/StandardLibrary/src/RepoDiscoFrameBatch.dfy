include "RepoDiscoU16Frame.dfy"

module RepoDiscoFrameBatch {
  import U = StandardLibrary.UInt
  import F = RepoDiscoU16Frame
  import opened Wrappers

  datatype Batch = Batch(payloads: seq<seq<U.uint8>>, rest: seq<U.uint8>)

  predicate method HasCountedFrames(input: seq<U.uint8>, count: nat)
    decreases count
  {
    count == 0 ||
      (F.HasFrame(input) && HasCountedFrames(F.FrameRest(input), count - 1))
  }

  predicate method BoundedPayloads(payloads: seq<seq<U.uint8>>)
    decreases |payloads|
  {
    |payloads| == 0 ||
      (U.HasUint16Len(payloads[0]) && BoundedPayloads(payloads[1..]))
  }

  function method EncodeFrames(payloads: seq<seq<U.uint8>>): seq<U.uint8>
    requires BoundedPayloads(payloads)
    decreases |payloads|
  {
    if |payloads| == 0 then []
    else U.UInt16ToSeq(|payloads[0]| as U.uint16) + payloads[0] +
         EncodeFrames(payloads[1..])
  }

  function method {:opaque} ReadCountedFrames(input: seq<U.uint8>, count: nat)
    : (result: Result<Batch, string>)
    ensures result.Success? <==> HasCountedFrames(input, count)
    ensures result.Success? ==> |result.value.payloads| == count
    ensures result.Success? ==> BoundedPayloads(result.value.payloads)
    ensures result.Success? ==>
      input == EncodeFrames(result.value.payloads) + result.value.rest
    ensures result.Success? ==>
      result.value.rest == input[|EncodeFrames(result.value.payloads)|..]
    decreases count
  {
    // BEGIN REPLACEMENT
    Failure("No decoded frames")
    // END REPLACEMENT
  }
}
