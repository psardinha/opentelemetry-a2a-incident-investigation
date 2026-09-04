package pt.example.stringutils.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.observation.annotation.Observed;
import pt.example.stringutils.simulator.DownstreamSimulator;

import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

import org.springframework.beans.factory.annotation.Value;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class StringUtilsService {
  private static final Logger log =LoggerFactory.getLogger(StringUtilsService.class);
  private final Counter requests;

  private final List<Runnable> downstreamScenarios;

  @Value("${delay.average.to.reply.in.ms:0}")
  private long avgDelayToReply;
  @Value("${prob.generating.exceptions:0}")
  private float probGeneratingExceptions;

  public StringUtilsService(MeterRegistry        meterRegistry,
                            DownstreamSimulator  downstream) {    
    this.downstreamScenarios = List.of(downstream::simulateDatabaseAccess,
                                       downstream::simulateExternalService,
                                       downstream::simulateInvalidData,
                                       downstream::simulateUnexpectedFailure);             
    this.requests = Counter.builder("string_requests_total").
                            description("Number of string utils calculations").register(meterRegistry);
  }

  private void sleepTime (String operName) {
    if (avgDelayToReply <= 0)
      return;
    try {
      long timeToSleep = ThreadLocalRandom.current().nextLong(0L, 2*avgDelayToReply);
      Thread.sleep(timeToSleep);
      if (ThreadLocalRandom.current().nextFloat() > probGeneratingExceptions && timeToSleep > 0.8 * avgDelayToReply)
        log.atWarn().setMessage("Excessive time").
                     addKeyValue("operation", operName).log(); 
    } catch (InterruptedException e) {}
  }

  private void callDownstream() {
    downstreamScenarios.get(ThreadLocalRandom.current().nextInt(downstreamScenarios.size())).run();
  }

  @Observed(name = "string.length", contextualName = "calculate string length")
  public int length(String value) {
    callDownstream();
    sleepTime("length");
    requests.increment();
    int result = value == null ? 0 : value.length();
    log.atInfo().setMessage("String length calculation completed").
                 addKeyValue("operation", "length").
                 addKeyValue("argument", value).
                 addKeyValue("result", result).log(); 
    return result;
  }

  @Observed(name = "string.reverse", contextualName = "reverses a string")
  public String reverse(String value) {
    callDownstream();
    sleepTime("revertion");
    requests.increment();
    String result;
    if (value == null)
      result = null;
    else {
      StringBuilder sb = new StringBuilder(value);
      result = sb.reverse().toString();
    }
    log.atInfo().setMessage("String revertion completed").
                 addKeyValue("operation", "revertion").
                 addKeyValue("argument", value).
                 addKeyValue("result", result).log();    
    return result;
  }
  
  @Observed(name = "string.upper", contextualName = "Uppercases a string")
  public String toUpper(String value) {
    callDownstream();
    sleepTime("uppercase");
    requests.increment();
    String result = value == null ? null : value.toUpperCase();
    log.atInfo().setMessage("String convertion to uppercase completed").
                 addKeyValue("operation", "uppercase").
                 addKeyValue("argument", value).
                 addKeyValue("result", result).log();
    return result;
  }
}
