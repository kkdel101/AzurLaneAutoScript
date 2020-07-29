import numpy as np

from module.base.timer import Timer
from module.base.utils import get_color
from module.combat.assets import GET_ITEMS_1, GET_ITEMS_2, GET_ITEMS_3
from module.logger import logger
from module.research.assets import *
from module.research.project import ResearchSelector
from module.ui.ui import page_research, RESEARCH_CHECK

RESEARCH_ENTRANCE = [ENTRANCE_1, ENTRANCE_2, ENTRANCE_3, ENTRANCE_4, ENTRANCE_5]
RESEARCH_STATUS = [STATUS_1, STATUS_2, STATUS_3, STATUS_4, STATUS_5]


class RewardResearch(ResearchSelector):
    _research_project_offset = 0
    _research_finished_index = 2

    def ensure_research_stable(self):
        self.wait_until_stable(STABLE_CHECKER)

    def _in_research(self):
        return self.appear(RESEARCH_CHECK, offset=(20, 20))

    def _research_has_finished_at(self, button):
        """
        Args:
            button (Button):

        Returns:
            bool: True if a research finished
        """
        color = get_color(self.device.image, button.area)
        if np.max(color) - np.min(color) < 40:
            logger.warning(f'Unexpected color: {color}')
        index = np.argmax(color)  # R, G, B
        if index == 1:
            return True  # Green
        elif index == 2:
            return False  # Blue
        else:
            logger.warning(f'Unexpected color: {color}')
            return False

    def research_has_finished(self):
        """
        Finished research should be auto-focused to the center, but sometimes didn't, due to an unknown game bug.
        This method will handle that.

        Returns:
            bool: True if a research finished
        """
        for index, button in enumerate(RESEARCH_STATUS):
            if self._research_has_finished_at(button):
                logger.attr('Research_finished', index)
                self._research_finished_index = index
                return True

        return False

    def research_reset(self, skip_first_screenshot=True, save_get_items=False):
        """
        Args:
            skip_first_screenshot (bool):
            save_get_items (bool):

        Returns:
            bool: If reset success.
        """
        if not self.appear(RESET_AVAILABLE):
            logger.info('Research reset unavailable')
            return False

        logger.info('Research reset')
        executed = False
        if save_get_items:
            self.device.save_screenshot('research_project', interval=0)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear_then_click(RESET_AVAILABLE, interval=10):
                continue
            if self.handle_popup_confirm('RESEARCH_RESET'):
                executed = True
                continue

            # End
            if executed and self._in_research():
                self.ensure_no_info_bar(timeout=3)  # Refresh success
                self.ensure_research_stable()
                break

        return True

    def research_select_quit(self, skip_first_screenshot=True):
        logger.info('Research select quit')
        click_timer = Timer(10)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(RESEARCH_UNAVAILABLE, offset=(20, 20)) \
                    or self.appear(RESEARCH_START, offset=(20, 20)) \
                    or self.appear(RESEARCH_STOP, offset=(20, 20)):
                if click_timer.reached():
                    self.device.click(RESEARCH_SELECT_QUIT)
                else:
                    click_timer.reset()
            else:
                self.wait_until_stable(STABLE_CHECKER_CENTER)
                break

    def research_select(self, priority, save_get_items=False):
        """
        Args:
            priority (list): A list of str and int, such as [2, 3, 0, 'reset']
            save_get_items (bool):

        Returns:
            bool: False if have been reset
        """
        if not len(priority):
            logger.info('No research project satisfies current filter')
            return True
        for project in priority:
            # priority example: ['reset', 'shortest']
            if project == 'reset':
                if self.research_reset(save_get_items=save_get_items):
                    return False
                else:
                    continue

            if isinstance(project, str):
                # priority example: ['shortest']
                if project == 'shortest':
                    self.research_select(self.research_sort_shortest(), save_get_items=save_get_items)
                elif project == 'cheapest':
                    self.research_select(self.research_sort_cheapest(), save_get_items=save_get_items)
                else:
                    logger.warning(f'Unknown select method: {project}')
                return True
            else:
                # priority example: [2, 3, 0]
                if self.research_project_start(project):
                    return True
                else:
                    continue

        logger.info('No research project started')
        return True

    def research_project_start(self, index, skip_first_screenshot=True):
        """
        Args:
            index (int): 0 to 4.
            skip_first_screenshot:

        Returns:
            bool: If start success.
        """
        logger.info(f'Research project: {index}')
        click_timer = Timer(10)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # Don't use interval here, RESEARCH_CHECK already appeared 5 seconds ago
            if click_timer.reached() and self.appear(RESEARCH_CHECK, offset=(20, 20)):
                i = (index - self._research_project_offset) % 5
                logger.info(f'Project offset: {self._research_project_offset}, project {index} is at {i}')
                self.device.click(RESEARCH_ENTRANCE[i])
                self._research_project_offset = (index - 2) % 5
                self.ensure_research_stable()
                click_timer.reset()
                continue
            if self.appear_then_click(RESEARCH_START, interval=10):
                continue
            if self.handle_popup_confirm('RESEARCH_START'):
                continue

            # End
            if self.appear(RESEARCH_STOP):
                self.research_select_quit()
                self.ensure_no_info_bar(timeout=3)  # Research started
                return True
            if self.appear(RESEARCH_UNAVAILABLE):
                logger.info('Not enough resources to start this project')
                self.research_select_quit()
                return False

    def research_receive(self, skip_first_screenshot=True, save_get_items=False):
        logger.info('Research receive')
        executed = False
        # Hacks to change save folder
        backup = self.config.SCREEN_SHOT_SAVE_FOLDER
        self.config.SCREEN_SHOT_SAVE_FOLDER = self.config.SCREEN_SHOT_SAVE_FOLDER_BASE

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.appear(RESEARCH_CHECK, interval=10):
                if save_get_items:
                    self.device.save_screenshot('research_project', interval=0)
                self.device.click(RESEARCH_ENTRANCE[self._research_finished_index])
                continue

            if self.appear(GET_ITEMS_1, interval=5):
                if save_get_items:
                    self.device.sleep(2)
                    self.device.screenshot()
                    self.device.save_screenshot('research_items')
                self.device.click(GET_ITEMS_RESEARCH_SAVE)
                executed = True
                continue
            if self.appear(GET_ITEMS_2, interval=5):
                if save_get_items:
                    self.device.sleep(3)
                    self.device.screenshot()
                    self.device.save_screenshot('research_items')
                self.device.click(GET_ITEMS_RESEARCH_SAVE)
                executed = True
                continue
            if self.appear(GET_ITEMS_3, interval=5):
                if save_get_items:
                    self.device.sleep(4)
                    self.device.screenshot()
                    self.device.save_screenshot('research_items')
                    self.device.swipe((0, 250), box=ITEMS_3_SWIPE.area, random_range=(-10, -10, 10, 10), padding=0)
                    self.device.sleep(2)
                    self.device.screenshot()
                    self.device.save_screenshot('research_items', interval=0)
                self.device.click(GET_ITEMS_RESEARCH_SAVE)
                executed = True
                continue

            # End
            if executed and self._in_research():
                self.ensure_research_stable()
                break

        self.config.SCREEN_SHOT_SAVE_FOLDER_FOLDER = backup

    def research_reward(self):
        """
        Receive research reward and start new research.
        Unable to detect research is running.

        Pages:
            in: page_research, stable.
            out: page_research, has research project information, but it's still page_research.
        """
        logger.hr('Research start')
        if self.research_has_finished():
            self.research_receive(save_get_items=self.config.ENABLE_SAVE_GET_ITEMS)
        else:
            logger.info('No research has finished')

        self._research_project_offset = 0

        for _ in range(2):
            self.research_detect(self.device.image)
            priority = self.research_sort_filter()
            result = self.research_select(priority, save_get_items=self.config.ENABLE_SAVE_GET_ITEMS)
            if result:
                break

    def handle_research_reward(self):
        """
        Pages:
            in: page_reward
            out: page_research or page_reward
        """
        if not self.config.ENABLE_RESEARCH_REWARD:
            return False

        if not self.appear(RESEARCH_FINISHED) and not self.appear(RESEARCH_PENDING):
            logger.info('No research finished or pending')
            return False

        self.ui_goto(page_research, skip_first_screenshot=True)
        self.ensure_research_stable()

        self.research_reward()

        return True
