include "UInt.dfy"
include "../../libraries/src/Wrappers.dfy"

module RepoDiscoU16Frame {
  import U = StandardLibrary.UInt
  import opened Wrappers

  datatype Frame = Frame(payload: seq<U.uint8>, rest: seq<U.uint8>)

  predicate method HasFrame(input: seq<U.uint8>) {
    2 <= |input| && 2 + (U.SeqToUInt16(input[..2]) as nat) <= |input|
  }

  function method FramePayload(input: seq<U.uint8>): seq<U.uint8>
    requires HasFrame(input)
  {
    input[2..2 + (U.SeqToUInt16(input[..2]) as nat)]
  }

  function method FrameRest(input: seq<U.uint8>): seq<U.uint8>
    requires HasFrame(input)
  {
    input[2 + (U.SeqToUInt16(input[..2]) as nat)..]
  }

  function method {:opaque} ReadU16Frame(input: seq<U.uint8>)
    : (result: Result<Frame, string>)
    ensures result.Success? <==> HasFrame(input)
    ensures result.Success? ==>
      result.value.payload == FramePayload(input) &&
      result.value.rest == FrameRest(input)
    ensures result.Success? ==> U.HasUint16Len(result.value.payload)
    ensures result.Success? ==>
      input == U.UInt16ToSeq(|result.value.payload| as U.uint16) +
               result.value.payload + result.value.rest
  {
    // BEGIN REPLACEMENT
    // END REPLACEMENT
  }
}

