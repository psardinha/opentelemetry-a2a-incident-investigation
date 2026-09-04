package pt.example.stringUtils.controller;

import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import pt.example.stringutils.controller.StringUtilsController;
import pt.example.stringutils.service.StringUtilsService;
import pt.example.stringutils.simulator.DownstreamSimulator;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.Mockito.mock;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class StringUtilsControllerTest {

private MockMvc mockMvc;
  @BeforeEach
  void setUp() {
    var meterRegistry = new SimpleMeterRegistry();
    var downstream = new DownstreamSimulator();
    var service = new StringUtilsService(meterRegistry, downstream);
    mockMvc = MockMvcBuilders.standaloneSetup(new StringUtilsController(service)).build();
  }

  @Test
  void returnsLengthAsJson() throws Exception {
    mockMvc.perform(get("/api/strings/length").param("value", "telemetry")).
            andExpect(status().isOk()).
            andExpect(content().json("{\"value\":\"telemetry\",\"length\":9}"));
  }
}
