function Min(a: int, b: int): int
  ensures Min(a, b) == a || Min(a, b) == b
  ensures Min(a, b) <= a && Min(a, b) <= b
{
  if a <= b then a else b
}

method CheckMin(a: int, b: int)
{
  var m := Min(a, b);
  assert m == a || m == b;
  assert m <= a && m <= b;
}
