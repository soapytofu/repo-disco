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

    if |input| < 2 then
      Failure("Input too short to read length")
    else
      var lenBytes := input[..2];
      var len := U.SeqToUInt16(lenBytes) as nat;
      if 2 + len > |input| then
        Failure("Input too short for frame payload")
      else
        var payload := input[2..2 + len];
        var rest := input[2 + len..];
        assert HasFrame(input);
        assert payload == FramePayload(input);
        assert rest == FrameRest(input);
        assert U.HasUint16Len(payload) by {
          assert len < U.UINT16_LIMIT;
          assert |payload| == len;
        }
        assert input == U.UInt16ToSeq(|payload| as U.uint16) + payload + rest by {
          U.UInt16SeqDeserializeSerialize(lenBytes);
          assert U.UInt16ToSeq(U.SeqToUInt16(lenBytes)) == lenBytes;
          assert |payload| as U.uint16 == U.SeqToUInt16(lenBytes);
          assert U.UInt16ToSeq(|payload| as U.uint16) == lenBytes;
          assert input[..2] + input[2..2 + len] + input[2 + len..] == input;
        }
        Success(Frame(payload, rest))
  
    // END REPLACEMENT
  }
}

