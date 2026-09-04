package pt.example.stringutils.exception;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestControllerAdvice
public class GlobalExceptionHandler  {
  private static final Logger log =LoggerFactory.getLogger(GlobalExceptionHandler.class);

  @ExceptionHandler({SomethingIsWrong.class, WrongData.class})
  @ResponseStatus(HttpStatus.BAD_REQUEST)
  public Map<String, Object> handleServiceDegradation(Exception ex) {
    log.atError().setMessage(ex.getMessage()).addKeyValue("exceptionType", ex.getClass().getSimpleName()).log();
    return Map.of("message", ex.getMessage());
  } 
  
  @ExceptionHandler({DatabaseProblem.class, AnyOtherProblem.class})
  @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
  public Map<String, Object> handleMoreServiceDegradation(Exception ex) {
    log.atError().setMessage(ex.getMessage()).addKeyValue("exceptionType", ex.getClass().getSimpleName()).log();
    return Map.of("message", ex.getMessage());
  }
}
