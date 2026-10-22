module MagnitudeFacts {
  export provides Magnitude, EstablishLowerBound

  opaque function Magnitude(x: int): int
  {
    if x >= 0 then x else -x
  }

  lemma EstablishLowerBound(x: int)
    ensures Magnitude(x) >= 0
  {
    reveal Magnitude();
  }
}
