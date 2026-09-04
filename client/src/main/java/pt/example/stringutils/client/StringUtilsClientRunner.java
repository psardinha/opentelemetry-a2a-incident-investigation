package pt.example.stringutils.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.net.HttpURLConnection;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadLocalRandom;

@Component
public class StringUtilsClientRunner implements ApplicationRunner {
  private static final Logger log = LoggerFactory.getLogger(StringUtilsClientRunner.class);
  private static final List<String> OPERATIONS = List.of("length", "reverse", "upper");
  private static final List<String> VALUES = List.of("observability", "spring boot", "java 25", "distributed systems", "LTGM");

  @Value("${string-utils-client.server-url:http://localhost:8080}")
  private String defaultServerUrl;
  
  private final HttpClient httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
  private volatile boolean running = true;
  private ExecutorService workers;

  public StringUtilsClientRunner() {}

  @Override
  public void run(ApplicationArguments arguments) {
    int threadCount = requiredPositiveInt(arguments, "threads", "1");
    String serverUrl = option(arguments, "server-url", defaultServerUrl).replaceAll("/$", "");
    workers = Executors.newFixedThreadPool(threadCount, runnable -> {Thread thread = new Thread(runnable);
                                                                     thread.setName("string-utils-client-" + thread.threadId());
                                                                     return thread;});
    for (int index = 0; index < threadCount; index++)
      workers.submit(() -> invokeContinuously(serverUrl));
    log.atInfo().setMessage("String utils client started").addKeyValue("threads", threadCount).
                                                           addKeyValue("serverUrl", serverUrl).log();
  }

  private void invokeContinuously(String serverUrl) {
    while (running) {
        String operation = OPERATIONS.get(ThreadLocalRandom.current().nextInt(OPERATIONS.size()));
        String value = VALUES.get(ThreadLocalRandom.current().nextInt(VALUES.size()));
        invoke(serverUrl, operation, value);
    }
  }

  private void invoke(String serverUrl, String operation, String value) {
    try {
      URI uri = URI.create(serverUrl + "/api/strings/" + operation + "?value=" + encode(value));
      HttpRequest request = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(5)).
                                                        header("Accept", "application/json").
                                                        GET().build();
      HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
      if (response.statusCode() == HttpURLConnection.HTTP_OK)
        log.atDebug().setMessage("String utils OK").
                      addKeyValue("operation", operation).
                      addKeyValue("status", response.statusCode()).
                      log();
      else                              
        log.atError().setMessage("String utils returned an HTTP error status").
                      addKeyValue("operation", operation).
                      addKeyValue("status", response.statusCode()).
                      log();
    } catch (Exception ex) {
      log.atError().setMessage(ex.getMessage()).
                    addKeyValue("operation", operation).
                    addKeyValue("exceptionType", ex.getClass().getSimpleName()).
                    log();      
    }
  }

  private static String encode(String value) {
    return java.net.URLEncoder.encode(value, java.nio.charset.StandardCharsets.UTF_8);
  }

  private static int requiredPositiveInt(ApplicationArguments arguments, String name, String defaultValue) {
    String value = arguments.getOptionValues(name) == null ? defaultValue : arguments.getOptionValues(name).getLast();
    try {
      int parsed = Integer.parseInt(value);
      if (parsed > 0)
        return parsed;
    } catch (NumberFormatException ignored) {}
    throw new IllegalArgumentException("--" + name + " must be a positive integer");
  }

  private static String option(ApplicationArguments arguments, String name, String defaultValue) {
    List<String> values = arguments.getOptionValues(name);
    return values == null || values.isEmpty() ? defaultValue : values.getLast();
  }

  @jakarta.annotation.PreDestroy
  void stop() {
    running = false;
    if (workers != null)
        workers.shutdownNow();
  }
}
