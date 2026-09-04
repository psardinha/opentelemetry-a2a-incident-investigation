package pt.example.stringutils.exception;

public class SomethingIsWrong extends RuntimeException {
  public SomethingIsWrong (String message) {
    super(message);
  }      
}
