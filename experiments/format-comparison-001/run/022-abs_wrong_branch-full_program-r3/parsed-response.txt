function Abs(x: int): int
  ensures Abs(x) >= 0
  ensures Abs(x) == x || Abs(x) == -x
{
  if x >= 0 then x else -x
}

method CheckAbs(x: int)
{
  var a := Abs(x);
  assert a >= 0;
  assert a == x || a == -x;
}
