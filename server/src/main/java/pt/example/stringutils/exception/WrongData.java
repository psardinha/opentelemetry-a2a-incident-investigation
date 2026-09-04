package pt.example.stringutils.exception;

public class WrongData extends RuntimeException {
  public WrongData (String message) {
    super(message);
  }     
}
