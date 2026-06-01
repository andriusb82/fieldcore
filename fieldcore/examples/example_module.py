from uniform_platform.core.base_module import BaseModule


class ExampleModule(BaseModule):
    def __init__(self):
        super().__init__()

    def run(self):
        self.logger.info('Example module started')


if __name__ == '__main__':
    module = ExampleModule()
    module.run()
