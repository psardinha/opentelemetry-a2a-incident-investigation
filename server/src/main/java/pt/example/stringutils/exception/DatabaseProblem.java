package pt.example.stringutils.exception;

public class DatabaseProblem extends RuntimeException {
  public DatabaseProblem (String message) {
    super(message);
  }
}
