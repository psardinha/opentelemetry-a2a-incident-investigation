package pt.example.stringutils.simulator;

import io.micrometer.observation.annotation.Observed;
import pt.example.stringutils.exception.DatabaseProblem;
import pt.example.stringutils.exception.AnyOtherProblem;
import pt.example.stringutils.exception.SomethingIsWrong;
import pt.example.stringutils.exception.WrongData;

import java.util.concurrent.ThreadLocalRandom;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

  
@Component
public class DownstreamSimulator {
  @Value("${prob.generating.exceptions:0}")
  private float probGeneratingExceptions;

  @Observed(name = "database.access", contextualName = "database query")
  public void simulateDatabaseAccess() {
    if (ThreadLocalRandom.current().nextFloat() < probGeneratingExceptions)
      throw new DatabaseProblem("DB_ACCESS_FAILURE_001: simulated database access failure");
  }

  @Observed(name = "external.service", contextualName = "external service call")
  public void simulateExternalService() {
    if (ThreadLocalRandom.current().nextFloat() < probGeneratingExceptions)
      throw new AnyOtherProblem("EXTERNAL_SERVICE_FAILURE_001: simulated external service failure");
  }

  @Observed(name = "input.validation", contextualName = "validate input")
  public void simulateInvalidData() {
    if (ThreadLocalRandom.current().nextFloat() < probGeneratingExceptions)
      throw new WrongData("INPUT_VALIDATION_FAILURE_001: simulated input validation failure");
  }

  @Observed(name = "business.validation", contextualName = "validate business rules")
  public void simulateUnexpectedFailure() {
    if (ThreadLocalRandom.current().nextFloat() < probGeneratingExceptions)
      throw new SomethingIsWrong("BUSINESS_RULE_FAILURE_001: simulated business rule validation failure");
  }    
}


