function Clamp(x: int, lo: int, hi: int): int
  requires lo <= hi
  ensures lo <= Clamp(x, lo, hi) <= hi
  ensures lo <= x <= hi ==> Clamp(x, lo, hi) == x
{
  if x < lo then lo else x
}

method CheckClamp(x: int, lo: int, hi: int)
  requires lo <= hi
{
  var result := Clamp(x, lo, hi);
  assert lo <= result <= hi;
  if lo <= x <= hi {
    assert result == x;
  }
}
